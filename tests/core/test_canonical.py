"""规范字节采用独立冻结向量；不以序列化器自身构造预期。"""

import hashlib
import json
import subprocess
import unittest

from packages.core.canonical import canonical_json, configuration_hash, parse_json


class CanonicalTests(unittest.TestCase):
    def test_known_bytes_and_hash(self):
        self.assertEqual(
            canonical_json({"b": [True, None, "中文"], "a": 1}),
            '{"a":1,"b":[true,null,"中文"]}'.encode(),
        )
        self.assertEqual(
            configuration_hash({}),
            "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
        )
        self.assertEqual(
            configuration_hash({"b": 2, "a": 1}), configuration_hash({"a": 1, "b": 2})
        )
        self.assertNotEqual(configuration_hash([1, 2]), configuration_hash([2, 1]))

    def test_utf16_order_escaping_and_no_normalization(self):
        self.assertEqual(
            canonical_json({"\ue000": 1, "😀": 2, "\r": 3}),
            '{"\\r":3,"😀":2,"\ue000":1}'.encode(),
        )
        self.assertEqual(
            canonical_json('\x00\b\t\n\f\r"\\/'), b'"\\u0000\\b\\t\\n\\f\\r\\"\\\\/"'
        )
        self.assertNotEqual(configuration_hash("é"), configuration_hash("e\u0301"))

    def test_invalid_or_lossy_values_rejected(self):
        for value in (
            1.0,
            float("nan"),
            float("inf"),
            2**53,
            -(2**53),
            {1: "坏键"},
            "\ud800",
            {"\udc00": 1},
            (1, 2),
        ):
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                canonical_json(value)
        self.assertEqual(canonical_json(2**53 - 1), b"9007199254740991")
        self.assertEqual(canonical_json(-(2**53 - 1)), b"-9007199254740991")

    def test_parse_rejects_duplicate_keys_and_float_tokens(self):
        for source in (
            '{"a":1,"a":2}',
            '{"x":{"a":1,"a":2}}',
            "1.0",
            "1e0",
            "NaN",
            "Infinity",
            "9007199254740992",
            '"\\ud800"',
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                parse_json(source)
        value = parse_json(' {"中": [false, null, -3]} ')
        self.assertEqual(
            configuration_hash(value),
            hashlib.sha256('{"中":[false,null,-3]}'.encode()).hexdigest(),
        )

    def test_javascript_bytes_and_hash_agree(self):
        # Node独立使用ECMAScript序列化与UTF-16排序，覆盖非BMP和数值样式键。
        source = r"""
const fs = require('node:fs');
const crypto = require('node:crypto');
function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
  }
  return JSON.stringify(value);
}
const values = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(values.map(value => {
  const bytes = canonical(value);
  return [bytes, crypto.createHash('sha256').update(bytes, 'utf8').digest('hex')];
})));
"""
        values = [
            {"10": 1, "2": 2, "😀": "中文", "\ue000": True},
            {"control": "\x00\n\t", "safe": 2**53 - 1},
            [None, "é", "e\u0301", -23],
        ]
        result = subprocess.run(
            ["node", "-e", source],
            input=json.dumps(values),
            text=True,
            capture_output=True,
            check=True,
        )
        for value, (encoded, digest) in zip(
            values, json.loads(result.stdout), strict=True
        ):
            self.assertEqual(canonical_json(value), encoded.encode())
            self.assertEqual(configuration_hash(value), digest)

    def test_cycles_fail_with_domain_error(self):
        value = []
        value.append(value)
        with self.assertRaises(ValueError):
            canonical_json(value)


if __name__ == "__main__":
    unittest.main()
