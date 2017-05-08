import os.path
import ConfigParser

class ComplexIniFile(object):

    def __init__(self, root_dir=None):
        self.root_dir = root_dir
        self.root = None
        self.parsers = []

    def read(self, file):
        self.root = ConfigParser.ConfigParser()
        self.root.optionxform = str # preserve case
        self.root.read(file)

        try:
            for name, value in self.root.items("Includes"):
                if name != "include":
                    raise ValueError("Invalid entry in `Includes` section: %s: %s" % (name, value))
                for file in value.split(","):
                    path = os.path.join(self.root_dir, file) if self.root_dir else file
                    sub_parser = ComplexIniFile(root_dir=self.root_dir)
                    sub_parser.read(path)
                    self.parsers.append(sub_parser)
        except ConfigParser.NoSectionError:
            pass

    def items(self, section):
        processed_names = set()
        try:
            for name, value in self.root.items(section):
                processed_names.add(name)
                yield (name, value)
        except ConfigParser.NoSectionError:
            pass
        for p in self.parsers:
            for name, value in p.items(section):
                if name not in processed_names:
                    processed_names.add(name)
                    yield (name, value)

if __name__ == "__main__":

    c = ComplexIniFile()
    c.read("test.cfg")
    for n, v in c.items("System"):
        print n, v
    
