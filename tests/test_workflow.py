import unittest

from braincheck.workflow.state_machine import State, StateMachine


class WorkflowTests(unittest.TestCase):
    def test_fixed_flow_rejects_protocol_skips(self) -> None:
        machine = StateMachine()
        with self.assertRaises(ValueError):
            machine.advance(State.SART)
        machine.advance(State.IDENTITY)
        self.assertEqual(machine.state, State.IDENTITY)


if __name__ == "__main__":
    unittest.main()

