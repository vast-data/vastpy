import io
import unittest
from contextlib import redirect_stdout

from vastpy.cli import tabulate


def _render(data):
    out = io.StringIO()
    with redirect_stdout(out):
        tabulate(data)
    return [line.rstrip() for line in out.getvalue().splitlines()]


class TabulateTest(unittest.TestCase):
    def test_multiline_cell_keeps_dict_order(self):
        lines = _render([{'name': 'x', 'cfg': {'a': 1, 'b': 2, 'c': 3}}])

        cells = [line.split('|')[1].strip() for line in lines[2:] if '|' in line]
        self.assertEqual(cells, ['a: 1', 'b: 2', 'c: 3'])

    def test_single_line_cells(self):
        lines = _render([{'id': 1, 'name': 'view1'}, {'id': 2, 'name': 'view2'}])

        self.assertEqual(lines[0].split('|')[0].strip(), 'id')
        self.assertIn('view1', lines[2])
        self.assertIn('view2', lines[3])


if __name__ == '__main__':
    unittest.main()
