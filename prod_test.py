import unittest
from auth_admin import GIVE_DEV_PERMISSIONS


class Production(unittest.TestCase):

    def test_no_dev_permissions(self):
        self.assertFalse(GIVE_DEV_PERMISSIONS)


if __name__ == '__main__':
    unittest.main()
