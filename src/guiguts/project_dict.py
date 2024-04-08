"""Project dictionary operations"""

import json
import os.path
from pathlib import Path
from guiguts.utilities import load_dict_from_json, load_wordfile_into_dict

GOOD_WORDS_KEY = "good words"
BAD_WORDS_KEY = "bad words"
GOOD_WORDS_FILENAME = "good_words.txt"
BAD_WORDS_FILENAME = "bad_words.txt"
PROJECT_DICT_FILENAME = "project_dict.json"


class ProjectDict:
    """Load, store & save project-specific spellings.

    Stored internally as two dictionaries for good and bad words for
    speed of access during spell checks, etc.
    Saved into json file as two lists, so easier for PPers to read
    and/or modify if needed.
    """

    def __init__(self) -> None:
        """Initialize ProjectDict."""
        self.reset()

    def save(self, textfile_path: str) -> None:
        """Save the project dictionary to a file.

        Name of dictionary is basename of main text file, with "_dict"
        added, and extension `.json`.

        Args:
            textfile_path: Full pathname of main text file.
        """
        dict_name = self._dict_name_from_file_name(textfile_path)
        project_dict = {}
        project_dict[GOOD_WORDS_KEY] = list(self.good_words.keys())
        project_dict[BAD_WORDS_KEY] = list(self.bad_words.keys())
        with open(dict_name, "w", encoding="utf-8") as fp:
            json.dump(project_dict, fp, indent=2, ensure_ascii=False)

    def load(self, textfile_path: str) -> None:
        """Load the project dictionary from a file if it exists.

        Name of dictionary is basename of main text file, with "_dict"
        added, and extension `.json`.

        Args:
            textfile_path: Full pathname of main text file.
        """
        self.reset()
        dict_name = self._dict_name_from_file_name(textfile_path)
        if os.path.exists(dict_name):
            if project_dict := load_dict_from_json(dict_name):
                for word in project_dict[GOOD_WORDS_KEY]:
                    self.good_words[word] = True
                for word in project_dict[BAD_WORDS_KEY]:
                    self.bad_words[word] = True

    def reset(self) -> None:
        """Reset the project dictionary."""
        self.good_words: dict[str, bool] = {}
        self.bad_words: dict[str, bool] = {}

    def add_good_bad_words(self, file_name: str, load_good_words: bool) -> bool:
        """Add words from good/bad_words file to project dictionary.

        Args:
            load_good_words: True to load good words, False to load bad words.

        Returns:
            True if good/bad words file exists.
        """
        path = Path(
            os.path.dirname(file_name),
            GOOD_WORDS_FILENAME if load_good_words else BAD_WORDS_FILENAME,
        )
        target_dict = self.good_words if load_good_words else self.bad_words
        return load_wordfile_into_dict(path, target_dict)

    def _dict_name_from_file_name(self, file_name: str) -> str:
        """Set project dictionary path name from given file name.

        Args:
            file_name: path name of main text file.

        Returns:
            path name of project dictionary file.
        """
        dir_name = os.path.dirname(file_name)
        return os.path.join(dir_name, PROJECT_DICT_FILENAME)

    def contains_words(self) -> bool:
        """Return whether project dictionary contains any good/bad words.

        Returns:
            True if dictionary contains any good/bad words.
        """
        return len(self.good_words) > 0 or len(self.bad_words) > 0

    def add_good_word(self, word: str) -> None:
        """Add a good word to the project dictionary.

        Args:
            word: The word to be added.
        """
        self.good_words[word] = True
