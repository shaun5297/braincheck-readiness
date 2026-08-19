import unittest

from braincheck.acquisition.discovery import discover


class _Info:
    def __init__(self, *, uid: str, source_id: str = "device-1", name: str = "EEG") -> None:
        self._uid = uid
        self._source_id = source_id
        self._name = name

    def uid(self) -> str:
        return self._uid

    def source_id(self) -> str:
        return self._source_id

    def name(self) -> str:
        return self._name

    def type(self) -> str:
        return "EEG"

    def channel_count(self) -> int:
        return 2

    def nominal_srate(self) -> float:
        return 250.0

    def hostname(self) -> str:
        return "device-host"


class DiscoveryTests(unittest.TestCase):
    def test_identical_multihomed_sighting_is_deduplicated(self) -> None:
        info = _Info(uid="same")
        found = discover(resolver=lambda _timeout: [info, info])
        self.assertEqual(tuple(found), ("eeg",))

    def test_distinct_devices_of_same_kind_are_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "重复设备流"):
            discover(resolver=lambda _timeout: [_Info(uid="one"), _Info(uid="two", source_id="device-2")])

    def test_anonymous_same_kind_streams_are_not_silently_merged(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "重复设备流"):
            discover(resolver=lambda _timeout: [_Info(uid="", source_id=""), _Info(uid="", source_id="")])


if __name__ == "__main__":
    unittest.main()
