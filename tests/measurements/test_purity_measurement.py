import pytest

import numpy as np
import pennylane as qml


def expected_purity_ising_xx(param):
    """Returns the analytical purity for subsystems of the IsingXX"""

    eig_1 = (1 + np.sqrt(1 - 4 * np.cos(param / 2) ** 2 * np.sin(param / 2) ** 2)) / 2
    eig_2 = (1 - np.sqrt(1 - 4 * np.cos(param / 2) ** 2 * np.sin(param / 2) ** 2)) / 2
    return eig_1**2 + eig_2**2


def expected_purity_grad_ising_xx(param):
    """The analytic gradient purity for the IsingXX"""

    eig_1 = (1 + np.sqrt(1 - 4 * np.cos(param / 2) ** 2 * np.sin(param / 2) ** 2)) / 2
    eig_2 = (1 - np.sqrt(1 - 4 * np.cos(param / 2) ** 2 * np.sin(param / 2) ** 2)) / 2
    grad_expected_purity = (
        2
        * eig_1
        * (np.sin(param / 2) ** 3 * np.cos(param / 2) - np.sin(param / 2) * np.cos(param / 2) ** 3)
        / np.sqrt(1 - 4 * np.sin(param / 2) ** 2 * np.cos(param / 2) ** 2)
    ) + (
        2
        * eig_2
        * (
            np.sin(param / 2)
            * np.cos(param / 2)
            * (np.cos(param / 2) ** 2 - np.sin(param / 2) ** 2)
        )
        / np.sqrt(1 - 4 * np.sin(param / 2) ** 2 * np.cos(param / 2) ** 2)
    )
    return grad_expected_purity


class TestPurity:
    """Tests for purity measurements"""

    devices = ["default.qubit", "lightning.qubit", "default.mixed"]
    grad_supported_devices = ["default.qubit", "default.mixed"]
    mix_supported_devices = ["default.mixed"]

    diff_methods = ["backprop", "finite-diff"]

    parameters = np.linspace(0, 2 * np.pi, 3)
    probs = np.array([0.001, 0.01, 0.1, 0.2])

    wires_list = [([0], True), ([1], True), ([0, 1], False)]

    @pytest.mark.parametrize("shots, shape", [(None, (1,)), (10, (1,)), ((1, 10), (2,))])
    def test_shape(self, shots, shape):
        """Test the ``shape`` method."""
        meas = qml.purity(wires=0)
        dev = qml.device("default.qubit", wires=1, shots=shots)
        assert meas.shape(dev) == shape

    @pytest.mark.parametrize("shots, shape", [(None, ()), (10, ()), ((1, 10), ((), ()))])
    def test_shape_new(self, shots, shape):
        """Test the ``shape_new`` method."""
        qml.enable_return()
        meas = qml.purity(wires=0)
        dev = qml.device("default.qubit", wires=1, shots=shots)
        assert meas.shape(dev) == shape
        qml.disable_return()

    @pytest.mark.parametrize("device", devices)
    @pytest.mark.parametrize("param", parameters)
    @pytest.mark.parametrize("wires,is_partial", wires_list)
    def test_IsingXX_qnode_purity(self, device, param, wires, is_partial):
        """Tests purity for a qnode"""

        dev = qml.device(device, wires=2)

        @qml.qnode(dev)
        def circuit(x):
            qml.IsingXX(x, wires=[0, 1])
            return qml.purity(wires=wires)

        purity = circuit(param)
        expected_purity = expected_purity_ising_xx(param) if is_partial else 1
        assert qml.math.allclose(purity, expected_purity)

    @pytest.mark.parametrize("device", mix_supported_devices)
    @pytest.mark.parametrize("wires,is_partial", wires_list)
    @pytest.mark.parametrize("param", probs)
    def test_bit_flip_qnode_purity(self, device, wires, param, is_partial):
        """Tests purity for a qnode on a noisy device with bit flips"""

        dev = qml.device(device, wires=2)

        @qml.qnode(dev)
        def circuit(p):
            qml.Hadamard(wires=0)
            qml.CNOT(wires=[0, 1])
            qml.BitFlip(p, wires=0)
            qml.BitFlip(p, wires=1)
            return qml.purity(wires=wires)

        purity = circuit(param)
        expected_purity = (
            0.5
            if is_partial
            else 4 * (0.5 - (1 - param) * param) ** 2 + 4 * (1 - param) ** 2 * param**2
        )
        assert qml.math.allclose(purity, expected_purity)

    @pytest.mark.parametrize("device", grad_supported_devices)
    @pytest.mark.parametrize("param", parameters)
    @pytest.mark.parametrize("wires,is_partial", wires_list)
    @pytest.mark.parametrize("diff_method", diff_methods)
    def test_IsingXX_qnode_purity_grad(self, device, param, wires, is_partial, diff_method):
        """Tests purity for a qnode"""

        dev = qml.device(device, wires=2)

        @qml.qnode(dev, diff_method=diff_method)
        def circuit(x):
            qml.IsingXX(x, wires=[0, 1])
            return qml.purity(wires=wires)

        grad_purity = qml.grad(circuit)(param)
        expected_grad = expected_purity_grad_ising_xx(param) if is_partial else 0
        assert qml.math.allclose(grad_purity, expected_grad, rtol=1e-04, atol=1e-05)

    @pytest.mark.parametrize("device", mix_supported_devices)
    @pytest.mark.parametrize("wires,is_partial", wires_list)
    @pytest.mark.parametrize("param", probs)
    @pytest.mark.parametrize("diff_method", diff_methods)
    def test_bit_flip_qnode_purity_grad(self, device, wires, param, is_partial, diff_method):
        """Tests gradient of purity for a qnode on a noisy device with bit flips"""

        dev = qml.device(device, wires=2)

        @qml.qnode(dev)
        def circuit(p):
            qml.Hadamard(wires=0)
            qml.CNOT(wires=[0, 1])
            qml.BitFlip(p, wires=0)
            qml.BitFlip(p, wires=1)
            return qml.purity(wires=wires)

        purity_grad = qml.grad(circuit)(param)
        expected_purity_grad = 0 if is_partial else 32 * (param - 0.5) ** 3
        assert qml.math.allclose(purity_grad, expected_purity_grad, rtol=1e-04, atol=1e-05)

    @pytest.mark.jax
    @pytest.mark.parametrize("device", devices)
    @pytest.mark.parametrize("param", parameters)
    @pytest.mark.parametrize("wires,is_partial", wires_list)
    def test_IsingXX_qnode_purity_jax(self, device, param, wires, is_partial):
        """Test purity for a QNode with jax interface."""

        import jax.numpy as jnp

        dev = qml.device(device, wires=2)

        @qml.qnode(dev, interface="jax")
        def circuit(x):
            qml.IsingXX(x, wires=[0, 1])
            return qml.purity(wires=wires)

        purity = circuit(jnp.array(param))
        expected_purity = expected_purity_ising_xx(param) if is_partial else 1
        assert qml.math.allclose(purity, expected_purity)

    @pytest.mark.jax
    @pytest.mark.parametrize("device", grad_supported_devices)
    @pytest.mark.parametrize("param", parameters)
    @pytest.mark.parametrize("wires,is_partial", wires_list)
    @pytest.mark.parametrize("diff_method", diff_methods)
    def test_IsingXX_qnode_purity_grad_jax(self, device, param, wires, is_partial, diff_method):
        """Test purity for a QNode gradient with Jax."""

        import jax

        dev = qml.device(device, wires=2)

        @qml.qnode(dev, interface="jax", diff_method=diff_method)
        def circuit(x):
            qml.IsingXX(x, wires=[0, 1])
            return qml.purity(wires=wires)

        grad_purity = jax.grad(circuit)(jax.numpy.array(param))
        grad_expected_purity = expected_purity_grad_ising_xx(param) if is_partial else 0

        assert qml.math.allclose(grad_purity, grad_expected_purity, rtol=1e-04, atol=1e-05)

    @pytest.mark.jax
    @pytest.mark.parametrize("device", devices)
    @pytest.mark.parametrize("param", parameters)
    @pytest.mark.parametrize("wires,is_partial", wires_list)
    def test_IsingXX_qnode_purity_jax_jit(self, device, param, wires, is_partial):
        """Test purity for a QNode with jax interface."""

        import jax
        import jax.numpy as jnp

        dev = qml.device(device, wires=2)

        @qml.qnode(dev, interface="jax-jit")
        def circuit(x):
            qml.IsingXX(x, wires=[0, 1])
            return qml.purity(wires=wires)

        purity = jax.jit(circuit)(jnp.array(param))
        expected_purity = expected_purity_ising_xx(param) if is_partial else 1
        assert qml.math.allclose(purity, expected_purity)

    @pytest.mark.jax
    @pytest.mark.parametrize("device", grad_supported_devices)
    @pytest.mark.parametrize("param", parameters)
    @pytest.mark.parametrize("wires,is_partial", wires_list)
    @pytest.mark.parametrize("diff_method", diff_methods)
    def test_IsingXX_qnode_purity_grad_jax_jit(self, device, param, wires, is_partial, diff_method):
        """Test purity for a QNode gradient with Jax."""

        import jax

        dev = qml.device(device, wires=2)

        @qml.qnode(dev, interface="jax-jit", diff_method=diff_method)
        def circuit(x):
            qml.IsingXX(x, wires=[0, 1])
            return qml.purity(wires=wires)

        grad_purity = jax.jit(jax.grad(circuit))(jax.numpy.array(param))
        grad_expected_purity = expected_purity_grad_ising_xx(param) if is_partial else 0

        assert qml.math.allclose(grad_purity, grad_expected_purity, rtol=1e-04, atol=1e-05)

    @pytest.mark.torch
    @pytest.mark.parametrize("device", devices)
    @pytest.mark.parametrize("param", parameters)
    @pytest.mark.parametrize("wires,is_partial", wires_list)
    def test_IsingXX_qnode_purity_torch(self, device, param, wires, is_partial):
        """Tests purity for a qnode"""

        import torch

        dev = qml.device(device, wires=2)

        @qml.qnode(dev, interface="torch")
        def circuit(x):
            qml.IsingXX(x, wires=[0, 1])
            return qml.purity(wires=wires)

        purity = circuit(torch.tensor(param))
        expected_purity = expected_purity_ising_xx(param) if is_partial else 1
        assert qml.math.allclose(purity, expected_purity)

    @pytest.mark.torch
    @pytest.mark.parametrize("device", grad_supported_devices)
    @pytest.mark.parametrize("param", parameters)
    @pytest.mark.parametrize("wires,is_partial", wires_list)
    @pytest.mark.parametrize("diff_method", diff_methods)
    def test_IsingXX_qnode_purity_grad_torch(self, device, param, wires, is_partial, diff_method):
        """Test purity for a QNode gradient with torch."""

        import torch

        dev = qml.device(device, wires=2)

        @qml.qnode(dev, interface="torch", diff_method=diff_method)
        def circuit(x):
            qml.IsingXX(x, wires=[0, 1])
            return qml.purity(wires=wires)

        expected_grad = expected_purity_grad_ising_xx(param) if is_partial else 0

        param = torch.tensor(param, dtype=torch.float64, requires_grad=True)
        purity = circuit(param)
        purity.backward()
        grad_purity = param.grad

        assert qml.math.allclose(grad_purity, expected_grad, rtol=1e-04, atol=1e-05)

    @pytest.mark.tf
    @pytest.mark.parametrize("device", devices)
    @pytest.mark.parametrize("param", parameters)
    @pytest.mark.parametrize("wires,is_partial", wires_list)
    def test_IsingXX_qnode_purity_tf(self, device, param, wires, is_partial):
        """Tests purity for a qnode"""

        import tensorflow as tf

        dev = qml.device(device, wires=2)

        @qml.qnode(dev, interface="tf")
        def circuit(x):
            qml.IsingXX(x, wires=[0, 1])
            return qml.purity(wires=wires)

        purity = circuit(tf.Variable(param))
        expected_purity = expected_purity_ising_xx(param) if is_partial else 1
        assert qml.math.allclose(purity, expected_purity)

    @pytest.mark.tf
    @pytest.mark.parametrize("device", grad_supported_devices)
    @pytest.mark.parametrize("param", parameters)
    @pytest.mark.parametrize("wires,is_partial", wires_list)
    @pytest.mark.parametrize("diff_method", diff_methods)
    def test_IsingXX_qnode_purity_grad_tf(self, device, param, wires, is_partial, diff_method):
        """Test purity for a QNode gradient with tf."""

        import tensorflow as tf

        dev = qml.device(device, wires=2)

        @qml.qnode(dev, interface="tf", diff_method=diff_method)
        def circuit(x):
            qml.IsingXX(x, wires=[0, 1])
            return qml.purity(wires=wires)

        grad_expected_purity = expected_purity_grad_ising_xx(param) if is_partial else 0

        param = tf.Variable(param)
        with tf.GradientTape() as tape:
            purity = circuit(param)

        grad_purity = tape.gradient(purity, param)

        assert qml.math.allclose(grad_purity, grad_expected_purity, rtol=1e-04, atol=1e-05)

    @pytest.mark.parametrize("device", devices)
    @pytest.mark.parametrize("param", parameters)
    def test_qnode_entropy_custom_wires(self, device, param):
        """Test that purity can be returned with custom wires."""

        dev = qml.device(device, wires=["a", 1])

        @qml.qnode(dev)
        def circuit(x):
            qml.IsingXX(x, wires=["a", 1])
            return qml.purity(wires=["a"])

        purity = circuit(param)
        expected_purity = expected_purity_ising_xx(param)
        assert qml.math.allclose(purity, expected_purity)
