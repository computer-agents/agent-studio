import platform

import pyperclip

from playground.desktop_env.computer.interpreter.python import Python
from playground.desktop_env.computer.interpreter.shell import Shell


class Os:
    def __init__(self, computer):
        self.computer = computer

        # clipboard
        if platform.uname()[0] != "Darwin":  # MacOS
            self.modifier_key = "ctrl"
        else:  # Linux or Windows
            self.modifier_key = "command"

        # terminal
        self.languages = [
            Python,
            Shell,
        ]
        self._active_languages = {}

    def view_clipboard(self):
        return pyperclip.paste()

    def copy(self, text=None):
        if text is not None:
            pyperclip.copy(text)
        else:
            self.computer.keyboard.hotkey(self.modifier_key, "c")

    def paste(self):
        self.computer.keyboard.hotkey(self.modifier_key, "v")

    def get_selected_text(self):
        # Store the current clipboard content
        current_clipboard = self.computer.os.view_clipboard()
        # Copy the selected text to clipboard
        self.computer.os.copy()
        # Get the selected text from clipboard
        selected_text = self.computer.os.view_clipboard()
        # Reset the clipboard to its original content
        self.computer.os.copy(current_clipboard)
        return selected_text

    def get_language(self, language):
        for lang in self.languages:
            if language.lower() == lang.name.lower() or (
                hasattr(lang, "aliases") and language in lang.aliases
            ):
                return lang
        return None

    def run(self, language, code):
        if language not in self._active_languages:
            self._active_languages[language] = self.get_language(language)()
        try:
            for chunk in self._active_languages[language].run(code):
                yield chunk

        except GeneratorExit:
            self.stop()

    def stop(self):
        for language in self._active_languages.values():
            language.stop()

    def terminate(self):
        for language_name in list(self._active_languages.keys()):
            language = self._active_languages[language_name]
            if (
                language
            ):  # Not sure why this is None sometimes. We should look into this
                language.terminate()
            del self._active_languages[language_name]
