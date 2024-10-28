import unittest
import tarfile
import os
import tempfile
from io import BytesIO
from unittest import mock
from unittest.mock import patch
import xml.etree.ElementTree as ET

# Import the FileSystemEmulator from main.py
from main import FileSystemEmulator

class TestFileSystemEmulator(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.TemporaryDirectory()

        # Paths for tar and log files
        self.tar_path = os.path.join(self.test_dir.name, 'test_fs.tar')
        self.log_path = os.path.join(self.test_dir.name, 'log.xml')

        # Create a sample tar file with a predefined directory structure
        with tarfile.open(self.tar_path, 'w') as tar:
            # Create directories
            tarinfo = tarfile.TarInfo(name='dir1/')
            tarinfo.type = tarfile.DIRTYPE
            tar.addfile(tarinfo)

            tarinfo = tarfile.TarInfo(name='dir1/subdir1/')
            tarinfo.type = tarfile.DIRTYPE
            tar.addfile(tarinfo)

            # Create files
            file1_data = b'Hello World!'
            tarinfo = tarfile.TarInfo(name='file1.txt')
            tarinfo.size = len(file1_data)
            tar.addfile(tarinfo, BytesIO(file1_data))

            file2_data = b'Test File in Subdir'
            tarinfo = tarfile.TarInfo(name='dir1/subdir1/file2.txt')
            tarinfo.size = len(file2_data)
            tar.addfile(tarinfo, BytesIO(file2_data))

        # Initialize the emulator
        self.emulator = FileSystemEmulator(
            tar_path=self.tar_path,
            hostname='test_host',
            log_file=self.log_path
        )

    def tearDown(self):
        # Clean up the temporary directory
        self.test_dir.cleanup()

    # --------------------- Tests for ls Command ---------------------
    @patch('builtins.print')
    def test_ls_root_directory(self, mock_print):
        """Test listing contents of the root directory."""
        self.emulator.current_path = "/"
        self.emulator.ls()
        expected = ['dir1', 'file1.txt']
        mock_print.assert_any_call('dir1')
        mock_print.assert_any_call('file1.txt')
        # Check logging
        tree = ET.parse(self.log_path)
        root = tree.getroot()
        last_action = root.findall('action')[-1]
        self.assertEqual(last_action.find('type').text, 'ls')
        self.assertEqual(last_action.find('details').text, 'Path: /')

    @patch('builtins.print')
    def test_ls_subdirectory(self, mock_print):
        """Test listing contents of a subdirectory."""
        self.emulator.current_path = "/dir1/"
        self.emulator.ls()
        expected = ['subdir1']
        mock_print.assert_any_call('subdir1')
        # Check logging
        tree = ET.parse(self.log_path)
        root = tree.getroot()
        last_action = root.findall('action')[-1]
        self.assertEqual(last_action.find('type').text, 'ls')
        self.assertEqual(last_action.find('details').text, 'Path: /dir1/')

    # --------------------- Tests for cd Command ---------------------
    @patch('builtins.print')
    def test_cd_existing_directory(self, mock_print):
        """Test changing to an existing subdirectory."""
        self.emulator.cd("dir1")
        self.assertEqual(self.emulator.current_path, "dir1")
        mock_print.assert_called_with("Changed directory to dir1")
        # Check logging
        tree = ET.parse(self.log_path)
        root = tree.getroot()
        last_action = root.findall('action')[-1]
        self.assertEqual(last_action.find('type').text, 'cd')
        self.assertEqual(last_action.find('details').text, 'Path: dir1')

    @patch('builtins.print')
    def test_cd_nonexistent_directory(self, mock_print):
        """Test attempting to change to a non-existent directory."""
        self.emulator.cd("nonexistent")
        self.assertEqual(self.emulator.current_path, "/")  # Should remain unchanged
        mock_print.assert_called_with("No such directory: nonexistent")
        # Check logging
        tree = ET.parse(self.log_path)
        root = tree.getroot()
        last_action = root.findall('action')[-1]
        self.assertEqual(last_action.find('type').text, 'cd')
        self.assertEqual(last_action.find('details').text, 'Failed to change directory to nonexistent')

    # --------------------- Tests for find Command ---------------------
    @patch('builtins.print')
    def test_find_existing_file(self, mock_print):
        """Test finding an existing file."""
        found = self.emulator.find("file2.txt")
        self.assertIn('dir1/subdir1/file2.txt', found)
        mock_print.assert_called_with('dir1/subdir1/file2.txt')
        # Check logging
        tree = ET.parse(self.log_path)
        root = tree.getroot()
        last_action = root.findall('action')[-1]
        self.assertEqual(last_action.find('type').text, 'find')
        self.assertEqual(last_action.find('details').text, 'Search: file2.txt, Results: 1')

    @patch('builtins.print')
    def test_find_nonexistent_file(self, mock_print):
        """Test attempting to find a non-existent file."""
        found = self.emulator.find("nonexistent.txt")
        self.assertEqual(len(found), 0)
        mock_print.assert_called_with('No files found matching: nonexistent.txt')
        # Check logging
        tree = ET.parse(self.log_path)
        root = tree.getroot()
        last_action = root.findall('action')[-1]
        self.assertEqual(last_action.find('type').text, 'find')
        self.assertEqual(last_action.find('details').text, 'Search: nonexistent.txt, No results')

    # --------------------- Tests for cp Command ---------------------
    @patch('builtins.print')
    def test_cp_existing_file(self, mock_print):
        """Test copying an existing file to a new destination."""
        destination = os.path.join(self.test_dir.name, 'copied_file1.txt')
        self.emulator.cp('file1.txt', destination)
        self.assertTrue(os.path.exists(destination))
        with open(destination, 'rb') as f:
            content = f.read()
        self.assertEqual(content, b'Hello World!')
        mock_print.assert_called_with(f"File copied from file1.txt to {destination}")
        # Check logging
        tree = ET.parse(self.log_path)
        root = tree.getroot()
        last_action = root.findall('action')[-1]
        self.assertEqual(last_action.find('type').text, 'cp')
        self.assertEqual(last_action.find('details').text, f"Copied from file1.txt to {destination}")

    @patch('builtins.print')
    def test_cp_nonexistent_file(self, mock_print):
        """Test attempting to copy a non-existent file."""
        destination = os.path.join(self.test_dir.name, 'copied_nonexistent.txt')
        self.emulator.cp('nonexistent.txt', destination)
        self.assertFalse(os.path.exists(destination))
        mock_print.assert_called_with("Source file not found: nonexistent.txt")
        # Check logging
        tree = ET.parse(self.log_path)
        root = tree.getroot()
        last_action = root.findall('action')[-1]
        self.assertEqual(last_action.find('type').text, 'cp')
        self.assertEqual(last_action.find('details').text, "Failed to copy from nonexistent.txt to " + destination)

if __name__ == '__main__':
    unittest.main()