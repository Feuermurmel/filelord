import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import typing


def is_subsequence_of(subseq, seq):
    # Subsequences of seq with the same length as subseq.
    def iter_subsequences():
        for i in range(len(seq) - len(subseq) + 1):
            yield seq[i:i + len(subseq)]

    return subseq in iter_subsequences()


def gather_duplicates(iter):
    def iter_duplicates():
        seen_elements = set()

        for i in iter:
            if i in seen_elements:
                yield i
            else:
                seen_elements.add(i)

    return list(iter_duplicates())


class FM:
    def __init__(self, root_dir):
        # The root directory of the repository used by this instance when
        # running commands. Can be changed when necessary.
        self.root_dir = root_dir

        # Set to a string, which indicates that the next use of __call__ is
        # expected to fail and produce the error message stored here.
        self._expect_error = None

        # Contains the output of the command which was last run as a string.
        self.output = None

        # The same output split into lines.
        self.lines = None

        # Caches the return value of the `index` property. Invalidated when a
        # command is run.
        self._cached_index = None

    # TODO: Do not run a subprocess for this. We gain very little by this.
    def __call__(self, cmdline, cwd='.'):
        """
        Run the filemaster command with the specified arguments and in the
        specified working directory. The working directory is relative to the
        root of the repository.
        """

        result = subprocess.run(
            ['filemaster', *cmdline.split()],
            cwd=str(self.root_dir / cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)

        # Write the captured output to stdout so that we see it in the
        # pytest output when a test fails.
        sys.stdout.buffer.write(result.stdout)

        self.output = result.stdout.decode()
        self.lines = self.output.splitlines()

        # Clear the FMIndex instance returned by self.index.
        self._cached_index = None

        # Make sure the application didn't crash, even when we expected a
        # non-zero returncode.
        assert 'Traceback' not in self.output

        # Reset value before checking the returncode.
        expect_error = self._expect_error
        self._expect_error = None

        if expect_error is None:
            assert result.returncode == 0
        else:
            assert result.returncode != 0
            self.check_output(expect_error)

    @property
    def index(self):
        if self._cached_index is None:
            self._cached_index = FMIndex(self)

        return self._cached_index

    def expect_error(self, error_message):
        """
        Call this before running a command to invert the logic which checks
        the exit status. The next call is expected to fail and produce the
        specified error message. This is reset after each command is executed.

        `error_message` can also be a `re.Pattern` instance.
        """

        self._expect_error = error_message

    def check_lines(self, *lines):
        """
        Check that `self.lines` contains each of the specified lines. This
        only matches full lines.
        """

        for i in lines:
            assert i in self.lines

    def check_consecutive_lines(self, *lines):
        """
        Check that `self.lines` contains all of the specified lines
        consecutively.
        """

        assert is_subsequence_of(list(lines), self.lines)

    def check_output(self, *strings):
        """
        Check that each of the strings is present in `self.output`. This
        checks substrings of the output.

        The elements of `string` can also be a regex pattern instances.
        """

        for i in strings:
            if isinstance(i, typing.re.Pattern):
                assert i.search(self.output)
            else:
                assert i in self.output

    def check_not_output(self, *strings):
        """
        Check that each of the strings is not present in `self.output`. This
        checks substrings of the output.

        The elements of `string` can also be a regex pattern instances.
        """

        for i in strings:
            if isinstance(i, typing.re.Pattern):
                assert not i.search(self.output)
            else:
                assert i not in self.output


class FMIndex:
    """
    Implementation for the `index` property of `FM` instances, which allows
    access to the repositories index.
    """

    def __init__(self, fm: FM):
        self._fm = fm

        def iter_entries():
            filelist_path = self._fm.root_dir / '.filemaster' / 'fileindex'

            with filelist_path.open('r', encoding='utf-8') as file:
                return [json.loads(i) for i in file]

        entries = list(iter_entries())

        # Check that there are not multiple entries for the same hash.
        assert len(gather_duplicates(i['hash'] for i in entries)) == 0

        self._entries_by_hash = {i['hash']: i for i in entries}

    def _entry_by_content(self, content):
        h = hashlib.sha256()
        h.update(content.encode())
        digest = 'sha256:' + h.digest().hex()

        return self._entries_by_hash.get(digest)

    @property
    def size(self):
        """
        Return the number of files currently in the index.
        """

        return len(self._entries_by_hash)

    def check_intended_path(self, content, intended_path):
        """
        Check that the intended path for the file with the specified content
        is set to the specified path. The content is hashed and its digest is
        looked up in the repository's index.
        """

        entry = self._entry_by_content(content)

        assert entry is not None
        assert entry['intended_path'] == intended_path

    def check_not_in_index(self, content):
        assert self._entry_by_content(content) is None


class Files:
    def __init__(self, root_dir: pathlib.Path):
        self._root_dir = root_dir

    def __contains__(self, item):
        """
        Return whether a something exists at the specified path relative to
        the root directory.
        """

        return (self._root_dir / item).exists()

    def __getitem__(self, item):
        """
        Read from a path relative to the root directory of the repository.
        For a file, its content will be returned as a string,
        for a directory, `...` will be returned.
        """

        path = self._root_dir / item

        if path.is_dir():
            return ...
        else:
            return path.read_text(encoding='utf-8')

    def __setitem__(self, item, value):
        """
        Write to a path relative to the root directory of the repository.
        Assigning a string will create a file with that content, assigning
        `...` will create a directory at that path. Missing parent
        directories are created as necessary.
        """

        path = self._root_dir / item

        path.parent.mkdir(parents=True, exist_ok=True)

        if value is ...:
            path.mkdir(exist_ok=True)
        else:
            return path.write_text(value, encoding='utf-8')

    def __delitem__(self, item):
        """
        Delete a file or directory at a path relative to the root directory
        of the repository.
        """

        path = self._root_dir / item

        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    @property
    def root(self):
        return self._root_dir
