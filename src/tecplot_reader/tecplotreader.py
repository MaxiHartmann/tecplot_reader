"""This module contains the class TecplotFile."""

import re
import numpy
import pandas

NUMBERFMT = "%-10.8e"


class TecplotFile:
    """
    A class for a tecplot file in ascii format.

    ...

    Attributes
    ----------
    variables : list
        List of variable names

    zone_list : dict
        Dictionary with zones as keys and all data as its values.
        Values are in array format.

    zone_lines : dict
        Dictionary with zones as keys and all data as its values but as strings.

    zone_names : list

    -------
    """

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
        value_lines = []

        with open(filename, "r", encoding="utf-8") as tecfile:
            for line in tecfile:
                match = title_pattern.search(line)
                if match:
                    self.title = match.group(1)
                    continue

                match = variables_pattern.search(line)
                if match:
                    self.variables = variable_pattern.findall(match.group(1))
                    continue

                match = auxdata_pattern.search(line)
                if match:
                    self.auxdata[match.group(1)] = match.group(2)
                    continue

                match = zone_auxdata_pattern.search(line)
                if match:
                    if zone:
                        self.zone_auxdata[zone][match.group(1)] = match.group(2)
                    continue

                match = varauxdata_pattern.search(line)
                if match:
                    var_index = int(match.group(1))
                    key = match.group(2)
                    value = match.group(3)
                    try:
                        var_name = self.variables[var_index - 1]
                        if var_name not in self.var_auxdata:
                            self.var_auxdata[var_name] = {}
                        self.var_auxdata[var_name][key] = value
                    except IndexError:
                        print(f"var_auxdata index {var_index} not found!")

                match = zone_pattern.search(line)
                if match:
                    if zone:
                        values = numpy.empty((len(value_lines), len(self.variables)))
                        for i, vline in enumerate(value_lines):
                            for j, val in enumerate([float(x) for x in vline]):
                                values[i, j] = val

                        self.zone_list[zone] = values
                        self.zone_lines[zone] = value_lines
                        value_lines = []
                    zone = match.group(1)
                    self.zone_names.append(zone)
                    self.zone_auxdata[zone] = {}
                    continue

                match = value_pattern.match(line)
                if zone and match:
                    value_lines.append(line.split())

                match = variable_pattern.search(line)
                if not zone and match:
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

    def get_variable_index(self, var_name):
        """
        Parameters:
            var_name (string): Name of the variable.

        Returns:
            int: The index of variables name.
        """
        return self.variables.index(var_name)


    def get_value(self, zone, var_index, i):
        """
        Parameters:
            zone (string): Name of the zone.

            var_index (int): Index of the variable.

            i (int): Row index.

        Returns:
            float: Value of row i for variable.
        """
        return self.zone_list[zone][i, var_index]

    def get_value_str(self, zone, var_index, i):
        """
        Parameters:
            zone (string): Name of the zone.

            var_index (int): Index of the variable.

            i (int): Row index.

        Returns:
            string: Value of row i for variable.
        """
        return self.zone_lines[zone][i][var_index]

    def set_value(self, zone, var_index, i, value):
        """
        Parameters:
            zone (string): Name of the zone.

            var_index (int): Index of the variable.

            i (int): Index of row in column of specified variable.

            value (float): New value of specified entry.

        """
        if isinstance(value, str):
            self.zone_list[zone][i, var_index] = float(value)
            self.zone_lines[zone][i][var_index] = value
        else:  # value is float
            self.zone_list[zone][i, var_index] = value
            self.zone_lines[zone][i][var_index] = NUMBERFMT % value

    def get_values(self, zone, var_index):
        """
        Parameters:
            zone (string): Name of the zone.

            var_index (int): Index of the variable.

        Returns:
            Column data of variable as 1d-array.
        """
        return self.zone_list[zone][:, var_index]

    def set_values(self, zone, var_index, var_values):
        """
        Parameters:
            zone (string): Name of the zone.

            var_index (int): Index of the variable.

            var_values (array or list): Must be the same size as in zone.
        """
        self.zone_list[zone][:, var_index] = var_values
        for i, value in enumerate(var_values):
            self.zone_lines[zone][i][var_index] = NUMBERFMT % value

    def get_value_size(self, zone):
        """
        Get the value 'i' of zone.

        Parameters:
            zone (string): Name of the zone.

            i (int): Index of of the row or line.
        """
        return self.zone_list[zone].shape[0]

    def get_value_line(self, zone, i):
        """
        Get the row 'i' of zone.

        Parameters:
            zone (string): Name of the zone.

            i (int): Index of of the row or line.

        Returns:
            1d-array of data.
        """
        return self.zone_list[zone][i, :]

    def __str__(self):
        """
        Returns the data as a string.

        Returns:
            string
        """
        line = f"Title: {self.title}\n"
        line += f"Variables: {','.join(self.variables)}\n"
        for item in self.auxdata.items():
            line += f'AuxData: {item} = "{item}"\n'
        for zone, values in self.zone_list.items():
            line += f"Zone: {zone} values: {values.shape}\n"
            line += values.__str__()
        return line

    def remove_variable(self, zone, var_name):
        """
        Deletes the specified variable in zone.

        Parameters:
            zone (string): Name of the zone.

            var_name (string): Name of the variable.
        """
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
        """
        Returns the data as a string that can be written to a file.

        Returns:
            string
        """
        string = ""
        string += f'TITLE = {self.title}"\n'
        string += "VARIABLES ="
        for var in self.variables:
            string += f' "{var}"'
        string += "\n"
        for key, value in self.auxdata.items():
            string += f'DATASETAUXDATA {key} = "{value}"\n'
        for zone, lines in self.zone_lines.items():
            string += f'ZONE T = "{zone}", I = {len(lines):d}, DATAPACKING = POINT\n'

            for line in lines:
                string += "  ".join(line) + "\n"

        return string

    def to_pandas(self, zone):
        """
        Returns the a pandas dataframe for the specified zone.

        Parameters:
            zone (string): Name of the zone.

        Returns:
            pandas.core.frame.DataFrame
        """
        data_dict = {}
        for i, var in enumerate(self.variables):
            data_dict[var] = self.get_values(zone, i)
        return pandas.DataFrame(data_dict)


if __name__ == "__main__":
    FILE = "../../data/tecplot.dat"
    data = TecplotFile(FILE)
    print(data.to_str())
