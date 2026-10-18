import contextlib
import io
import json
import unittest

import helpers
from nightlight import cli, config, indicators, lifecycle

SHELL = {
    "version": 1,
    "bar": {
        "position": "top",
        "layout": {
            "left": [{"id": "omarchy.menu"}],
            "center": [
                {"id": "omarchy.clock", "format": "HH:mm"},
                {"id": "mystical.indicators"},
            ],
            "right": [{"id": "mystical.audio"}],
        },
    },
    "idle": {"lock": 300},
}


def run_cli(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(list(argv))
    return code, out.getvalue()


class ShellTest(helpers.SandboxTest):
    def write_shell(self, shell=None):
        config.SHELL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        config.SHELL_CONFIG.write_text(json.dumps(shell or SHELL, indent=2) + "\n")

    def shell(self):
        return json.loads(config.SHELL_CONFIG.read_text())

    def indicators_entry(self):
        return self.shell()["bar"]["layout"]["center"][1]


class Hide(ShellTest):
    def test_explicit_items_lose_the_toggle(self):
        shell = json.loads(json.dumps(SHELL))
        shell["bar"]["layout"]["center"][1]["items"] = ["Dictation", "NightLight", "Dnd"]
        self.write_shell(shell)
        self.assertEqual(indicators.hide(), 1)
        self.assertEqual(self.indicators_entry()["items"], ["Dictation", "Dnd"])

    def test_defaults_become_explicit_without_the_toggle(self):
        self.write_shell()
        self.assertEqual(indicators.hide(), 1)
        self.assertEqual(self.indicators_entry()["items"],
                         ["Dictation", "ScreenRecording", "Reminder", "Dnd", "StayAwake"])

    def test_other_entries_and_keys_survive(self):
        self.write_shell()
        indicators.hide()
        shell = self.shell()
        self.assertEqual(shell["bar"]["layout"]["left"], [{"id": "omarchy.menu"}])
        self.assertEqual(shell["bar"]["layout"]["center"][0],
                         {"id": "omarchy.clock", "format": "HH:mm"})
        self.assertEqual(shell["idle"], {"lock": 300})
        self.assertEqual(shell["bar"]["position"], "top")

    def test_backup_is_written_once(self):
        self.write_shell()
        indicators.hide()
        backup = config.SHELL_CONFIG.with_name("shell.json.pre-nightlight")
        self.assertEqual(json.loads(backup.read_text()), SHELL)
        indicators.restore()
        indicators.hide()
        self.assertEqual(json.loads(backup.read_text()), SHELL)

    def test_already_hidden_is_a_no_op(self):
        self.write_shell()
        self.assertEqual(indicators.hide(), 1)
        self.assertEqual(indicators.hide(), 0)

    def test_no_shell_config(self):
        self.assertEqual(indicators.hide(), 0)
        self.assertFalse(config.INDICATORS_STATE.exists())
        self.assertFalse(indicators.hidden())

    def test_no_indicators_widget(self):
        self.write_shell({"bar": {"layout": {"left": [{"id": "omarchy.menu"}]}}})
        self.assertEqual(indicators.hide(), 0)
        self.assertFalse(config.INDICATORS_STATE.exists())

    def test_broken_json_is_left_alone(self):
        config.SHELL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        config.SHELL_CONFIG.write_text("{not json")
        self.assertEqual(indicators.hide(), 0)
        self.assertEqual(config.SHELL_CONFIG.read_text(), "{not json")


class Restore(ShellTest):
    def test_explicit_items_come_back(self):
        shell = json.loads(json.dumps(SHELL))
        shell["bar"]["layout"]["center"][1]["items"] = ["Dictation", "NightLight", "Dnd"]
        self.write_shell(shell)
        indicators.hide()
        self.assertEqual(indicators.restore(), 1)
        self.assertEqual(self.indicators_entry()["items"], ["Dictation", "NightLight", "Dnd"])
        self.assertFalse(config.INDICATORS_STATE.exists())

    def test_unset_items_are_unset_again(self):
        self.write_shell()
        indicators.hide()
        indicators.restore()
        self.assertNotIn("items", self.indicators_entry())

    def test_restore_without_state_is_a_no_op(self):
        self.write_shell()
        before = config.SHELL_CONFIG.read_text()
        self.assertEqual(indicators.restore(), 0)
        self.assertEqual(config.SHELL_CONFIG.read_text(), before)

    def test_state_file_is_validated(self):
        self.write_shell()
        config.INDICATORS_STATE.parent.mkdir(parents=True, exist_ok=True)
        config.INDICATORS_STATE.write_text(json.dumps({"version": 1, "widgets": "nope"}))
        with helpers.quiet():
            self.assertEqual(indicators.restore(), 0)
        self.assertNotIn("items", self.indicators_entry())


class Lifecycle(ShellTest):
    def test_enable_hides_the_toggle(self):
        self.write_conf()
        self.write_shell()
        self.assertEqual(lifecycle.enable(dict(config.DEFAULTS)), 1)
        self.assertTrue(indicators.hidden())
        self.assertEqual(self.indicators_entry()["items"],
                         ["Dictation", "ScreenRecording", "Reminder", "Dnd", "StayAwake"])

    def test_enable_survives_a_missing_shell_config(self):
        self.write_conf()
        self.assertEqual(lifecycle.enable(dict(config.DEFAULTS)), 0)
        self.assertTrue(lifecycle.enabled())

    def test_disable_restores_the_toggle(self):
        self.write_conf()
        self.write_shell()
        lifecycle.enable(dict(config.DEFAULTS))
        lifecycle.disable()
        self.assertNotIn("items", self.indicators_entry())
        self.assertFalse(indicators.hidden())

    def test_enable_cli_prints_the_hint(self):
        self.write_conf()
        self.write_shell()
        code, out = run_cli("enable")
        self.assertEqual(code, 0)
        self.assertIn("removed Omarchy's own Night Light toggle", out)
        self.assertIn("hl.unbind(\"SUPER + CTRL + N\")", out)

    def test_json_report_carries_the_flag(self):
        self.write_conf()
        self.write_shell()
        lifecycle.enable(dict(config.DEFAULTS))
        _, out = run_cli("status", "--json")
        self.assertTrue(json.loads(out)["bar"]["nightLightToggleHidden"])


if __name__ == "__main__":
    unittest.main()
