import json
import struct
import tempfile
import unittest
from pathlib import Path

import azrok_admin


class AdminProjectionTests(unittest.TestCase):
    def test_list_detail_and_edit_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            key = 'a74657374_s2_c506574'
            snapshot = bytearray(0xC4)
            snapshot[5] = 1
            struct.pack_into('<H', snapshot, 0x0A + 2, 12)
            state = {
                'schema_version': 1, 'revision': 3, 'currency': 123,
                'character': {'species': 2}, 'snapshot_hex': snapshot.hex(),
                'inventory': {name: [0] * size for name, size in azrok_admin.INVENTORY_SIZES.items()},
                'runtime_rows': [{'kind': 1, 'aux': 31, 'value': 26080406}],
            }
            (Path(directory) / (key + azrok_admin.STATE_SUFFIX)).write_text(
                json.dumps(state), encoding='utf-8')
            (Path(directory) / 'deleted').mkdir()
            (Path(directory) / 'deleted' / (key + azrok_admin.STATE_SUFFIX)).write_text(
                json.dumps(state), encoding='utf-8')
            summary = azrok_admin.list_characters(directory)
            self.assertEqual(1, len(summary))
            self.assertEqual('state_file_mtime_not_login', summary[0]['activity_basis'])
            detail = azrok_admin.character_detail(directory, key)
            self.assertEqual(('test', 'Pet', 2),
                             (detail['account'], detail['name'], detail['slot']))
            self.assertEqual((1, 12, 123),
                             (detail['evolution'], detail['level'], detail['currency']))
            self.assertNotIn('snapshot_hex', detail)
            self.assertEqual(('food', 0, 255),
                             azrok_admin.validate_inventory_edit('food', 0, 255))
            self.assertEqual(0xFFFFFFFF, azrok_admin.validate_currency_edit(0xFFFFFFFF))
            view = azrok_admin.character_admin_view(directory, key)
            self.assertEqual('이유식', next(i['name'] for i in view['inventory']
                                           if i['item_id'] == 1000))
            self.assertTrue(next(i['reserved'] for i in view['inventory']
                                 if i['item_id'] == 1033))
            self.assertEqual(1, view['active_quests'][0]['kind'])
            self.assertEqual(12, view['stats'][1])
            accounts = azrok_admin.list_accounts(directory, {
                'accounts': [{'account': 'test', 'binding_count': 1}]},
                [{'account': 'test'}])
            self.assertEqual((1, True, 1),
                             (len(accounts), accounts[0]['online'], accounts[0]['binding_count']))
            patch = azrok_admin.validate_patch(state, {
                'expected_revision': 3, 'currency': 7,
                'inventory': [{'name': 'food', 'slot': 0, 'quantity': 2}],
            })
            self.assertEqual(2, patch['inventory'][0]['quantity'])

    def test_rejects_path_traversal_and_invalid_edits(self):
        for key in ('../outside', 'a00_s4_c00', 'a00_s0_c00_state_v1.json'):
            with self.assertRaises(ValueError):
                azrok_admin.parse_character_key(key)
        for edit in (('food', 38, 1), ('food', 33, 1), ('food', 0, 256),
                     ('toy', 0, 2), ('food', True, 1), ('invalid', 0, 1)):
            with self.assertRaises(ValueError):
                azrok_admin.validate_inventory_edit(*edit)
        for value in (-1, 0x100000000, True, '1'):
            with self.assertRaises(ValueError):
                azrok_admin.validate_currency_edit(value)
        with self.assertRaises(ValueError):
            azrok_admin.validate_patch({'revision': 1}, {'expected_revision': 0, 'currency': 1})


if __name__ == '__main__':
    unittest.main()
