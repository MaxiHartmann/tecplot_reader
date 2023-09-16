import re
import timeit
import numpy
import pandas

# import time

NUMBERFMT = "%-10.8e"


class TecplotFile:
    def __init__(self, filename):
        title_pattern = re.compile(r'TITLE\s*="([^"]+)"')
        variables_pattern = re.compile(r'VARIABLES\s*=(([,\s]*"([^"]+)")+)')
        variable_pattern = re.compile(r'"([^"]+)"')
        auxdata_pattern = re.compile(r'DATASETAUXDATA\s*([^\s]+)\s*=\s*"([^"]+)"')
        varauxdata_pattern = re.compile(
            r'VARAUXDATA\s+(\d+)\s*([^\s]+)\s*=\s*"([^"]+)"'
        )
        zone_pattern = re.compile(r'ZONE\s+T\s*=\s*"([^"]+)"')
        zone_auxdata_pattern = re.compile(r'^\s*AUXDATA\s*([^\s]+)\s*=\s*"([^"]+)"')
        value_pattern = re.compile(r"(\s*[+-]?\d+[.]?\d*e?[+-]?\d*)+")
        zone = False
        self.variables = []
        self.zone_list = {}
        self.zone_lines = {}
        self.zone_names = []
        self.auxdata = {}
        self.var_auxdata = {}
        self.zone_auxdata = {}
        self.first_zone_name = False
        value_lines = []

        with open(filename, "r", encoding="utf-8") as tecfile:
            for line in tecfile:
                matches = title_pattern.search(line)
                if matches:
                    self.title = matches.group(1)
                    continue

                matches = variables_pattern.search(line)
                if matches:
                    self.variables = variable_pattern.findall(matches.group(1))
                    continue

                matches = auxdata_pattern.search(line)
                if matches:
                    self.auxdata[matches.group(1)] = matches.group(2)
                    continue

                matches = zone_auxdata_pattern.search(line)
                if matches:
                    if zone:
                        self.zone_auxdata[zone][matches.group(1)] = matches.group(2)
                    continue

                matches = varauxdata_pattern.search(line)
                if matches:
                    var_index = int(matches.group(1))
                    key = matches.group(2)
                    value = matches.group(3)
                    try:
                        var_name = self.variables[var_index - 1]
                        if var_name not in self.var_auxdata:
                            self.var_auxdata[var_name] = {}
                        self.var_auxdata[var_name][key] = value
                    except IndexError:
                        print(f"var_auxdata index {var_index} not found!")

                matches = zone_pattern.search(line)
                if matches:
                    if zone:
                        values = numpy.empty((len(value_lines), len(self.variables)))
                        for i, vline in enumerate(value_lines):
                            for j, val in enumerate([float(x) for x in vline]):
                                values[i, j] = val

                        self.zone_list[zone] = values
                        self.zone_lines[zone] = value_lines
                        value_lines = []
                        if not self.first_zone_name:
                            self.first_zone_name = zone
                    zone = matches.group(1)
                    self.zone_names.append(zone)
                    self.zone_auxdata[zone] = {}
                    continue

                matches = value_pattern.match(line)
                if zone and matches:
                    value_lines.append(line.split())

                matches = variable_pattern.search(line)
                if not zone and matches:
                    self.variables.extend(variable_pattern.findall(line))
                    continue

            if zone:
                values = numpy.arange(
                    len(value_lines) * len(self.variables), dtype=float
                ).reshape(len(value_lines), len(self.variables))

                for i, vline in enumerate(value_lines):
                    for j, val in enumerate([float(x) for x in vline]):
                        values[i, j] = val

                    self.zone_list[zone] = values
                    self.zone_lines[zone] = value_lines
                    if not self.first_zone_name:
                        self.first_zone_name = zone

    def get_variable_index(self, var_name):
        return self.variables.index(var_name)

    def get_value(self, zone, var_index, i):
        return self.zone_list[zone][i, var_index]

    def get_value_str(self, zone, var_index, i):
        return self.zone_lines[zone][i][var_index]

    def set_value(self, zone, var_index, i, value):
        if isinstance(value, str):
            self.zone_list[zone][i, var_index] = float(value)
            self.zone_lines[zone][i][var_index] = value
        else:  # value is float
            self.zone_list[zone][i, var_index] = value
            self.zone_lines[zone][i][var_index] = NUMBERFMT % value

    def get_values(self, zone, var_index):
        return self.zone_list[zone][:, var_index]

    def set_values(self, zone, var_index, var_values):
        self.zone_list[zone][:, var_index] = var_values
        for i, value in enumerate(var_values):
            self.zone_lines[zone][i][var_index] = NUMBERFMT % value

    def get_value_size(self, zone):
        return self.zone_list[zone].shape[0]

    def get_value_line(self, zone, i):
        return self.zone_list[zone][i, :]

    def __str__(self):
        line = f"Title: {self.title}\n"
        line += f"Variables: {','.join(self.variables)}\n"
        for item in self.auxdata.items():
            line += f'AuxData: {item} = "{item}"\n'
        for zone, values in self.zone_list.items():
            line += f"Zone: {zone} values: {values.shape}\n"
            line += values.__str__()
        return line

    def remove_variable(self, zone, var_name):
        var_index = self.variables.index(var_name)
        if var_index < 0:
            return

        self.variables = self.variables[:var_index] + self.variables[var_index + 1 :]
        lines = []
        for line in self.zone_lines[zone]:
            lines.append(line[:var_index] + line[var_index + 1 :])
        self.zone_lines[zone] = lines
        i = [True] * self.zone_list[zone].shape[1]
        i[var_index] = False

        values = self.zone_list[zone].compress(i, axis=1)
        self.zone_list[zone] = values

    def to_str(self):
        string = ""
        string += f'TITLE = {self.title}"\n'
        string += "VARIABLES ="
        for var in self.variables:
            string += f' "{var}"'
        string += "\n"
        for aux in self.auxdata.items():
            string += f'DATASETAUXDATA {aux} = "{aux}"\n'
        for zone, lines in self.zone_lines.items():
            string += f'ZONE T = "{zone}", I = {len(lines):d}, DATAPACKING = POINT\n'

            for line in lines:
                string += "  ".join(line) + "\n"

        return string

    def to_pandas(self, zone):
        data_dict = {}
        for i, var in enumerate(self.variables):
            data_dict[var] = self.get_values(zone, i)
        return pandas.DataFrame(data_dict)


if __name__ == "__main__":
    FILE = "../data/tecplot.dat"

    def test_1():
        """read testfile"""
        title = "Simple Data File"
        zone_names = ["Zone 1", "Zone 2"]
        auxdata = {"Alpha": "5", "Pi": "3.14 "}
        testdata = TecplotFile(FILE)

        assert testdata.title == title, title
        assert testdata.first_zone_name == zone_names[0], zone_names[0]
        result = testdata.get_values("Zone 2", 1)
        reference = [1.0, 1.0e-04, 2.0, 0.1, 9.0234]
        numpy.testing.assert_allclose(result, reference, rtol=1e-5, atol=0)

        assert testdata.auxdata == auxdata, auxdata
        assert testdata.zone_names == zone_names, zone_names

    time_1 = timeit.timeit("test_1()", setup="from __main__ import test_1", number=1)
    print(f"time_1 = {time_1:.8f}")

    data = TecplotFile(FILE)
