import os
import tarfile
import argparse
import xml.etree.ElementTree as ET
import xml.dom.minidom
from datetime import datetime


class FileSystemEmulator:
    def __init__(self, tar_path, hostname, log_file):
        self.tar_path = tar_path
        self.hostname = hostname
        self.log_file = log_file
        self.current_path = "/"
        self.fs_tree = self.load_tar_fs()
        self.init_log()

    def load_tar_fs(self):
        """Загружаем структуру tar-файла в виртуальную файловую систему."""
        fs = {}
        with tarfile.open(self.tar_path, 'r') as tar:
            for member in tar.getmembers():
                # Normalize path separators to '/'
                member.name = member.name.replace('\\', '/')
                fs[member.name.rstrip('/')] = member
        return fs

    def init_log(self):
        """Инициализация XML-лог-файла."""
        self.root = ET.Element("session")
        self.tree = ET.ElementTree(self.root)

    def prettify_log(self):
        """Форматирование XML с отступами."""
        rough_string = ET.tostring(self.root, 'utf-8')
        reparsed = xml.dom.minidom.parseString(rough_string)
        with open(self.log_file, 'w') as f:
            f.write(reparsed.toprettyxml(indent="  "))

    def log_action(self, action, details=""):
        """Логирование действия в XML с датой и временем."""
        entry = ET.SubElement(self.root, "action")
        timestamp = ET.SubElement(entry, "timestamp")
        timestamp.text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        action_type = ET.SubElement(entry, "type")
        action_type.text = action
        if details:
            action_details = ET.SubElement(entry, "details")
            action_details.text = details
        self.prettify_log()

    def ls(self, path=None):
        """Эмуляция команды ls."""
        path = path or self.current_path
        normalized_path = path.rstrip('/').replace('\\', '/').lstrip('/')

        for item in self.fs_tree:
            parent_dir = os.path.dirname(item.rstrip('/')).replace('\\', '/')
            if parent_dir == normalized_path:
                print(os.path.basename(item.rstrip('/')))
        self.log_action("ls", f"Path: {path}")

    def cd(self, path=None):
        """Эмуляция команды cd с поддержкой относительных путей."""
        if path is None:
            path = "/"

        if path == "..":
            if self.current_path != "/":
                self.current_path = os.path.dirname(self.current_path.rstrip('/')).replace('\\', '/')
                self.current_path = self.current_path if self.current_path else "/"
                print(f"Changed directory to {self.current_path}")
                self.log_action("cd", f"Path: {self.current_path}")
            else:
                print("Already at the root directory")
                self.log_action("cd", "Failed to move up from root")
        else:
            # Handle absolute and relative paths
            if path.startswith("/"):
                new_path = path.lstrip('/')
            else:
                new_path = os.path.join(self.current_path, path).replace('\\', '/').rstrip('/')

            normalized_new_path = new_path

            if normalized_new_path in self.fs_tree and self.fs_tree[normalized_new_path].isdir():
                self.current_path = normalized_new_path
                print(f"Changed directory to {self.current_path}")
                self.log_action("cd", f"Path: {self.current_path}")
            elif normalized_new_path.lstrip('/') in self.fs_tree and self.fs_tree[normalized_new_path.lstrip('/')].isdir():
                self.current_path = normalized_new_path.lstrip('/')
                print(f"Changed directory to {self.current_path}")
                self.log_action("cd", f"Path: {self.current_path}")
            else:
                print(f"No such directory: {path}")
                self.log_action("cd", f"Failed to change directory to {path}")

    def find(self, search_name):
        """Эмуляция команды find."""
        found = [item for item in self.fs_tree if search_name in os.path.basename(item)]

        if found:
            for item in found:
                print(item)
            self.log_action("find", f"Search: {search_name}, Results: {len(found)}")
        else:
            print(f"No files found matching: {search_name}")
            self.log_action("find", f"Search: {search_name}, No results")
        
        return found

    def cp(self, source, destination):
        """Эмуляция команды cp."""
        normalized_source = source.lstrip('/')
        if normalized_source not in self.fs_tree:
            print(f"Source file not found: {source}")
            self.log_action("cp", f"Failed to copy from {source} to {destination}")
            return

        source_member = self.fs_tree[normalized_source]

        if source_member.isdir():
            print(f"Source is a directory, not a file: {source}")
            self.log_action("cp", f"Failed to copy directory {source} to {destination}")
            return

        if os.path.exists(destination):
            print(f"Destination already exists: {destination}")
            self.log_action("cp", f"Failed to copy to {destination} as it already exists")
            return

        with tarfile.open(self.tar_path, 'r') as tar:
            with tar.extractfile(source_member) as source_file, open(destination, 'wb') as dest_file:
                dest_file.write(source_file.read())

        print(f"File copied from {source} to {destination}")
        self.log_action("cp", f"Copied from {source} to {destination}")

    def run(self):
        """Запуск интерфейса командной строки."""
        while True:
            cmd = input(f"{self.hostname}:{self.current_path}> ").strip().split()
            if not cmd:
                continue
            command = cmd[0]
            args = cmd[1:] if len(cmd) > 1 else []

            if command == "ls":
                self.ls(*args)
            elif command == "cd":
                self.cd(*args)
            elif command == "find":
                self.find(*args)
            elif command == "cp":
                self.cp(*args)
            elif command == "exit":
                self.log_action("exit", "User exited the session")
                break
            else:
                print(f"Unknown command: {command}")
                self.log_action("unknown_command", f"Command: {command}")