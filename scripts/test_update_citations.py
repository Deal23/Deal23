import unittest

import update_citations as citations


def row(title, count):
    return (f'<tr class="gsc_a_tr"><td><a class="gsc_a_at">{title}</a></td>'
            f'<td class="gsc_a_c"><a>{count}</a></td></tr>')


class CitationTests(unittest.TestCase):
    def setUp(self):
        self.html = '<td class="gsc_rsb_std">1,234</td>' + ''.join(
            row(title, count) for title, count in zip(citations.PAPERS.values(), ['5', '', '12', '3'])
        )

    def test_parse_and_update(self):
        counts = citations.parse(self.html)
        self.assertEqual(counts['total'], 1234)
        self.assertEqual(counts['10.1007/s10853-025-11121-z'], 0)
        updated = citations.update_readme(citations.README.read_text(encoding='utf-8'), counts)
        self.assertIn('Google%20Scholar%20citations-1234-blue', updated)
        self.assertIn('citations-0-blue', updated)
        self.assertNotIn('citations-pending-lightgrey', updated)

    def test_incomplete_or_ambiguous_response_fails(self):
        with self.assertRaises(ValueError):
            citations.parse('<html>blocked</html>')
        with self.assertRaises(ValueError):
            citations.parse(self.html + row(next(iter(citations.PAPERS.values())), '9'))

    def test_missing_badge_fails(self):
        with self.assertRaises(ValueError):
            citations.update_readme('missing badges', citations.parse(self.html))


if __name__ == '__main__':
    unittest.main()
