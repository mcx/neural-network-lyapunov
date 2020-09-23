import neural_network_lyapunov.relu_to_optimization as relu_to_optimization
import unittest
import numpy as np
import torch
import torch.nn as nn
import cvxpy as cp


class TestReLU(unittest.TestCase):
    def setUp(self):
        self.dtype = torch.float64
        self.linear1 = nn.Linear(2, 3)
        self.linear1.weight.data = torch.tensor(
            [[1, 2], [3, 4], [5, 6]], dtype=self.dtype)
        self.linear1.bias.data = torch.tensor(
            [-11, 13, 4], dtype=self.dtype)
        self.linear1_no_bias = nn.Linear(2, 3, bias=False)
        self.linear1_no_bias.weight.data = self.linear1.weight.data.clone()

        self.linear2 = nn.Linear(3, 4)
        self.linear2.weight.data = torch.tensor(
            [[-1, 0.5, 1.5], [2, 5, 6], [-2, -3, -4], [1, 4, 6]],
            dtype=self.dtype)
        self.linear2.bias.data = torch.tensor(
            [4, -1, -2, -20], dtype=self.dtype)
        self.linear2_no_bias = nn.Linear(3, 4, bias=False)
        self.linear2_no_bias.weight.data = self.linear2.weight.data.clone()

        self.linear3 = nn.Linear(4, 1)
        self.linear3.weight.data = torch.tensor(
            [[4, 5, 6, 7]], dtype=self.dtype)
        self.linear3.bias.data = torch.tensor([-10], dtype=self.dtype)
        self.linear3_no_bias = nn.Linear(4, 1, bias=False)
        self.linear3_no_bias.weight.data = self.linear3.weight.data.clone()
        # Model with a ReLU unit in the output layer
        self.model1 = nn.Sequential(self.linear1, nn.ReLU(), self.linear2,
                                    nn.ReLU(), self.linear3, nn.ReLU())
        # Model without a ReLU unit in the output layer
        self.model2 = nn.Sequential(self.linear1, nn.ReLU(), self.linear2,
                                    nn.ReLU(), self.linear3)

        # Model with leaky ReLU with a leaky ReLU unit in the output layer.
        self.leaky_relus =\
            [nn.LeakyReLU(0.1), nn.LeakyReLU(-0.2), nn.LeakyReLU(0.01)]
        self.model3 = nn.Sequential(
            self.linear1, self.leaky_relus[0], self.linear2,
            self.leaky_relus[1], self.linear3, self.leaky_relus[2])
        # Model with leaky ReLU with no ReLU unit in the output layer.
        self.model4 = nn.Sequential(
            self.linear1, self.leaky_relus[0], self.linear2,
            self.leaky_relus[1], self.linear3)

        # Model with leaky ReLU but no bias term
        self.model5 = nn.Sequential(
            self.linear1_no_bias, self.leaky_relus[0], self.linear2_no_bias,
            self.leaky_relus[1], self.linear3_no_bias)

        # Model with multiple outputs, normal relu
        self.model6 = nn.Sequential(
            self.linear1, nn.ReLU(), self.linear2)
        # Model with multiple outputs, leaky relu
        self.model7 = nn.Sequential(
            self.linear1, self.leaky_relus[0], self.linear2)

    def test_compute_relu_activation_pattern1(self):
        x = torch.tensor([-6, 4], dtype=self.dtype)
        activation_pattern = relu_to_optimization.ComputeReLUActivationPattern(
            self.model1, x)
        self.assertEqual(len(activation_pattern), 3)
        self.assertEqual(len(activation_pattern[0]), 3)
        self.assertEqual(len(activation_pattern[1]), 4)
        self.assertEqual(len(activation_pattern[2]), 1)
        x_linear1 = self.linear1.forward(x)
        x_relu1 = nn.ReLU().forward(x_linear1)
        for i in range(3):
            self.assertEqual(x_linear1[i] >= 0, activation_pattern[0][i])
        x_linear2 = self.linear2.forward(x_relu1)
        for i in range(4):
            self.assertEqual(x_linear2[i] >= 0, activation_pattern[1][i])
        x_relu2 = nn.ReLU().forward(x_linear2)
        x_linear3 = self.linear3.forward(x_relu2)
        self.assertEqual(len(activation_pattern[2]), 1)
        self.assertEqual(x_linear3[0] >= 0, activation_pattern[2][0])

    def test_compute_relu_activation_pattern2(self):
        x = torch.tensor([-6, 4], dtype=self.dtype)
        activation_pattern = relu_to_optimization.ComputeReLUActivationPattern(
            self.model2, x)
        self.assertEqual(len(activation_pattern), 2)
        self.assertEqual(len(activation_pattern[0]), 3)
        self.assertEqual(len(activation_pattern[1]), 4)
        x_linear1 = self.linear1.forward(x)
        x_relu1 = nn.ReLU().forward(x_linear1)
        for i in range(3):
            self.assertEqual(x_linear1[i] >= 0, activation_pattern[0][i])
        x_linear2 = self.linear2.forward(x_relu1)
        for i in range(4):
            self.assertEqual(x_linear2[i] >= 0, activation_pattern[1][i])

    def test_compute_relu_activation_pattern3(self):
        # Test with leaky relu.
        def test_fun(x):
            activation_pattern = relu_to_optimization.\
                ComputeReLUActivationPattern(self.model3, x)
            self.assertEqual(len(activation_pattern), 3)
            self.assertEqual(len(activation_pattern[0]), 3)
            self.assertEqual(len(activation_pattern[1]), 4)
            self.assertEqual(len(activation_pattern[2]), 1)
            x_linear1 = self.linear1.forward(x)
            x_relu1 = self.leaky_relus[0].forward(x_linear1)
            for i in range(3):
                self.assertEqual(x_linear1[i] >= 0, activation_pattern[0][i])
            x_linear2 = self.linear2.forward(x_relu1)
            for i in range(4):
                self.assertEqual(x_linear2[i] >= 0, activation_pattern[1][i])
            x_relu2 = self.leaky_relus[1].forward(x_linear2)
            x_linear3 = self.linear3.forward(x_relu2)
            self.assertEqual(x_linear3[0] >= 0, activation_pattern[2][0])

        test_fun(torch.tensor([-1, 2], dtype=self.dtype))
        test_fun(torch.tensor([-1, 3], dtype=self.dtype))
        test_fun(torch.tensor([4, 3], dtype=self.dtype))
        test_fun(torch.tensor([-10, -4], dtype=self.dtype))

    def test_compute_all_relu_activation_patterns(self):
        linear1 = nn.Linear(2, 3)
        linear1.weight.data = torch.tensor(
            [[1, 2], [3, 4], [5, 6]], dtype=self.dtype)
        linear1.bias.data = torch.tensor(
            [-11, 13, 4], dtype=self.dtype)
        linear2 = nn.Linear(3, 3)
        linear2.weight.data = torch.tensor(
            [[3, -2, -1], [1, -4, 0], [0, 1, -2]], dtype=self.dtype)
        linear2.bias.data = torch.tensor(
            [-11, 13, 48], dtype=self.dtype)
        relu = nn.Sequential(linear1, nn.ReLU(), linear2, nn.ReLU())

        # For this input, all ReLU unit inputs are either > 0 or < 0
        patterns = relu_to_optimization.compute_all_relu_activation_patterns(
            relu, torch.tensor([1, 2], dtype=self.dtype))
        self.assertEqual(len(patterns), 1)
        self.assertEqual(
            patterns[0], [[False, True, True], [False, False, True]])

        # For this input, the input to first layer relu are [0, 36, 39], and
        # the input to the second layer relu are [-122, -131, 6]. Note that
        # one of the input is 0.
        patterns = relu_to_optimization.compute_all_relu_activation_patterns(
            relu, torch.tensor([1, 5], dtype=self.dtype))
        self.assertEqual(len(patterns), 2)
        self.assertEqual(
            patterns[0], [[True, True, True], [False, False, True]])
        self.assertEqual(
            patterns[1], [[False, True, True], [False, False, True]])

        # For this input, the input to first layer relu are [0, 0, -33], and
        # the input to the second layer relu are [-11, 13, 38]. Note that
        # two of the inputs are 0.
        patterns = relu_to_optimization.compute_all_relu_activation_patterns(
            relu, torch.tensor([-35, 23], dtype=self.dtype))
        self.assertEqual(len(patterns), 4)
        self.assertEqual(
            patterns[0], [[True, True, False], [False, True, True]])
        self.assertEqual(
            patterns[1], [[True, False, False], [False, True, True]])
        self.assertEqual(
            patterns[2], [[False, True, False], [False, True, True]])
        self.assertEqual(
            patterns[3], [[False, False, False], [False, True, True]])

        # For this input, the input to first layer relu are [0, 38, 43], and
        # the input to the second layer relu are [-130, -139, 0]. Note that
        # two of the inputs are 0.
        patterns = relu_to_optimization.compute_all_relu_activation_patterns(
            relu, torch.tensor([3, 4], dtype=self.dtype))
        self.assertEqual(len(patterns), 4)
        self.assertEqual(
            patterns[0], [[True, True, True], [False, False, True]])
        self.assertEqual(
            patterns[1], [[True, True, True], [False, False, False]])
        self.assertEqual(
            patterns[2], [[False, True, True], [False, False, True]])
        self.assertEqual(
            patterns[3], [[False, True, True], [False, False, False]])

    def test_relu_activation_binary_to_pattern(self):
        for model in (self.model1, self.model3):
            activation_pattern = \
                relu_to_optimization.relu_activation_binary_to_pattern(
                    model, np.array([1, 1, 0, 0, 1, 0, 0, 1]))
            self.assertEqual(
                activation_pattern,
                [[True, True, False], [False, True, False, False], [True]])
        for model in (self.model2, self.model4):
            activation_pattern = \
                relu_to_optimization.relu_activation_binary_to_pattern(
                    model, np.array([1, 1, 0, 0, 1, 0, 0]))
            self.assertEqual(
                activation_pattern,
                [[True, True, False], [False, True, False, False]])

    def test_relu_given_activation_pattern(self):
        def test_relu_given_activation_pattern_util(self, model, x):
            with torch.no_grad():
                activation_pattern = relu_to_optimization.\
                    ComputeReLUActivationPattern(model, x)
                (g, h, P, q) = relu_to_optimization.ReLUGivenActivationPattern(
                    model, 2, activation_pattern, self.dtype)
            x.requires_grad = True
            output_expected = model.forward(x)
            output_expected.backward()
            np.testing.assert_allclose(
                x.grad.detach().numpy(), g.squeeze().detach().numpy())
            with torch.no_grad():
                output = (g.T @ x.reshape((2, 1)) + h).item()
                self.assertAlmostEqual(output, output_expected.item(), 10)
                self.assertTrue(torch.all(torch.le(
                    P @ (x.reshape((-1, 1))), q)))
                # Randomly take 100 sample of inputs. If the sample shares the
                # same activation path as x, then it should satisfy P * x <= q
                # constraint. Otherwise it should violate the constraint.
                for _ in range(100):
                    x_sample = torch.tensor(
                        [np.random.uniform(-10, 10),
                         np.random.uniform(-10, 10)],
                        dtype=self.dtype)
                    activation_pattern_sample =\
                        relu_to_optimization.ComputeReLUActivationPattern(
                            model, x_sample)
                    output_sample_expected = model.forward(x_sample)
                    if (activation_pattern_sample == activation_pattern):
                        output_sample = g.T @ x_sample.reshape((2, 1)) + h
                        self.assertAlmostEqual(
                            output_sample.item(),
                            output_sample_expected.item(), 10)
                        self.assertTrue(
                            torch.all(torch.le(
                                P @ (x_sample.reshape((-1, 1))), q)))
                    else:
                        self.assertFalse(
                            torch.all(torch.le(
                                P @ (x_sample.reshape((-1, 1))), q)))

        for model in (self.model1, self.model2, self.model3, self.model4,
                      self.model5):
            test_relu_given_activation_pattern_util(
                self, model, torch.tensor([-6, 4], dtype=self.dtype))
            test_relu_given_activation_pattern_util(
                self, model, torch.tensor([-10, 4], dtype=self.dtype))
            test_relu_given_activation_pattern_util(
                self, model, torch.tensor([3, -4], dtype=self.dtype))
            test_relu_given_activation_pattern_util(
                self, model, torch.tensor([-3, -4], dtype=self.dtype))
            test_relu_given_activation_pattern_util(
                self, model, torch.tensor([-10, -20], dtype=self.dtype))

    def test_relu_free_pattern_constructor1(self):
        relu_free_pattern = relu_to_optimization.ReLUFreePattern(self.model1,
                                                                 self.dtype)
        self.assertTrue(relu_free_pattern.last_layer_is_relu)
        self.assertEqual(len(relu_free_pattern.relu_unit_index), 3)
        self.assertListEqual(relu_free_pattern.relu_unit_index[0], [0, 1, 2])
        self.assertListEqual(
            relu_free_pattern.relu_unit_index[1], [3, 4, 5, 6])
        self.assertListEqual(
            relu_free_pattern.relu_unit_index[2], [7])
        self.assertEqual(relu_free_pattern.num_relu_units, 8)

    def test_relu_free_pattern_constructor2(self):
        relu_free_pattern = relu_to_optimization.ReLUFreePattern(self.model2,
                                                                 self.dtype)
        self.assertFalse(relu_free_pattern.last_layer_is_relu)
        self.assertEqual(len(relu_free_pattern.relu_unit_index), 2)
        self.assertListEqual(relu_free_pattern.relu_unit_index[0], [0, 1, 2])
        self.assertListEqual(
            relu_free_pattern.relu_unit_index[1], [3, 4, 5, 6])
        self.assertEqual(relu_free_pattern.num_relu_units, 7)

    def test_relu_free_pattern_output_constraint(self):
        def test_model(model):
            relu_free_pattern = relu_to_optimization.ReLUFreePattern(
                model, self.dtype)
            x_lo = torch.tensor([-1, -2], dtype=self.dtype)
            x_up = torch.tensor([2, 3], dtype=self.dtype)
            (mip_constr_return,
                z_pre_relu_lo, z_pre_relu_up, z_post_relu_lo, z_post_relu_up)\
                = relu_free_pattern.output_constraint(x_lo, x_up)
            self.assertIsNone(mip_constr_return.Aout_input)
            self.assertIsNone(mip_constr_return.Aout_binary)
            # print("z_pre_relu_lo:{}\nz_pre_relu_up:{}".format(
            #    z_pre_relu_lo, z_pre_relu_up))
            num_z_pre_relu_lo_positive = np.sum([
                z_pre_relu_lo_i >= 0 for z_pre_relu_lo_i in z_pre_relu_lo])
            num_z_pre_relu_up_negative = np.sum([
                z_pre_relu_up_i <= 0 for z_pre_relu_up_i in z_pre_relu_up])
            num_ineq = (
                relu_free_pattern.num_relu_units - num_z_pre_relu_lo_positive
                - num_z_pre_relu_up_negative) * 4 + 4
            num_eq = (num_z_pre_relu_lo_positive + num_z_pre_relu_up_negative)\
                * 2
            self.assertListEqual(
                list(mip_constr_return.Ain_input.shape), [num_ineq, 2])
            self.assertListEqual(list(mip_constr_return.Ain_slack.shape), [
                                 num_ineq, relu_free_pattern.num_relu_units])
            self.assertListEqual(list(mip_constr_return.Ain_binary.shape), [
                                 num_ineq, relu_free_pattern.num_relu_units])
            self.assertListEqual(
                list(mip_constr_return.rhs_in.shape), [num_ineq, 1])
            self.assertListEqual(
                list(mip_constr_return.Aeq_input.shape), [num_eq, 2])
            self.assertListEqual(list(mip_constr_return.Aeq_slack.shape), [
                                 num_eq, relu_free_pattern.num_relu_units])
            self.assertListEqual(list(mip_constr_return.Aeq_binary.shape), [
                                 num_eq, relu_free_pattern.num_relu_units])
            self.assertListEqual(
                list(mip_constr_return.rhs_eq.shape), [num_eq, 1])

            def test_input_output(x):
                (z, beta, output) = \
                    relu_free_pattern.compute_relu_unit_outputs_and_activation(
                    x)
                # Now formulate an optimization problem, with fixed input,
                # search for z and beta. There should be only one solution.
                z_var = cp.Variable(relu_free_pattern.num_relu_units)
                beta_var = cp.Variable(relu_free_pattern.num_relu_units,
                                       boolean=True)
                x_np = x.detach().numpy()
                con = []
                if mip_constr_return.rhs_in.shape[0] != 0:
                    con.append(
                        mip_constr_return.Ain_input.detach().numpy() @ x_np +
                        mip_constr_return.Ain_slack.detach().numpy() @ z_var +
                        mip_constr_return.Ain_binary.detach().numpy() @
                        beta_var <=
                        mip_constr_return.rhs_in.squeeze().detach().numpy())
                if mip_constr_return.rhs_eq.shape[0] != 0:
                    con.append(
                        mip_constr_return.Aeq_input.detach().numpy() @ x_np +
                        mip_constr_return.Aeq_slack.detach().numpy() @ z_var +
                        mip_constr_return.Aeq_binary.detach().numpy() @
                        beta_var ==
                        mip_constr_return.rhs_eq.squeeze().detach().numpy())
                objective = cp.Minimize(0.)
                prob = cp.Problem(objective, con)
                prob.solve(solver=cp.GUROBI)
                if torch.all(x <= x_up) and torch.all(x >= x_lo):
                    self.assertEqual(prob.status, "optimal")
                    z_opt_var = z_var.value
                    beta_opt_var = beta_var.value
                    np.testing.assert_array_almost_equal(
                        z_opt_var, z.squeeze().detach().numpy())
                    np.testing.assert_array_almost_equal(
                        beta_opt_var, beta.squeeze().detach().numpy())
                    if len(mip_constr_return.Aout_slack.shape) > 1:
                        out_opt = mip_constr_return.Aout_slack @ z.squeeze()\
                            + mip_constr_return.Cout
                        output = model.forward(x)
                        for k in range(len(output)):
                            self.assertAlmostEqual(output[k], out_opt[k])
                    else:
                        self.assertAlmostEqual(
                            (mip_constr_return.Aout_slack @ z.squeeze() +
                             mip_constr_return.Cout).item(),
                            model.forward(x).item())
                else:
                    self.assertEqual(prob.status, "infeasible")

            def test_input_x(x):
                # For an arbitrary input x, compute its activation pattern and
                # output of each ReLU unit, check if they satisfy the
                # constraint
                # Ain1*x+Ain2*z+Ain3*β <= rhs_in
                # Aeq1*x+Aeq2*z+Aeq3*β <= rhs_eq
                assert(torch.all(torch.ge(x, x_lo.squeeze())))
                assert(torch.all(torch.le(x, x_up.squeeze())))
                (z, beta, output) = \
                    relu_free_pattern.compute_relu_unit_outputs_and_activation(
                    x)
                z_post_relu_up_numpy =\
                    np.array([zi.detach().numpy() for zi in z_post_relu_up])
                z_post_relu_lo_numpy =\
                    np.array([zi.detach().numpy() for zi in z_post_relu_lo])
                np.testing.assert_array_less(
                    z.squeeze().detach().numpy(), z_post_relu_up_numpy + 1E-10)
                np.testing.assert_array_less(
                    z_post_relu_lo_numpy - 1E-10, z.squeeze().detach().numpy())
                # Check the output
                if isinstance(output, torch.Tensor):
                    out_opt = mip_constr_return.Aout_slack @ z.squeeze() +\
                        mip_constr_return.Cout
                    for k in range(len(output)):
                        self.assertAlmostEqual(output[k], out_opt[k], 3)
                else:
                    self.assertAlmostEqual(
                        output, (mip_constr_return.Aout_slack.T @ z +
                                 mip_constr_return.Cout).item(), 3)
                x_vec = x.reshape((-1, 1))
                lhs_in = mip_constr_return.Ain_input @ x_vec +\
                    mip_constr_return.Ain_slack @ z +\
                    mip_constr_return.Ain_binary @ beta
                lhs_eq = mip_constr_return.Aeq_input @ x_vec +\
                    mip_constr_return.Aeq_slack @ z +\
                    mip_constr_return.Aeq_binary @ beta
                precision = 1E-10
                np.testing.assert_array_less(
                    lhs_in.squeeze().detach().numpy(),
                    mip_constr_return.rhs_in.squeeze().detach().numpy() +
                    precision)
                np.testing.assert_allclose(
                    lhs_eq.squeeze().detach().numpy(),
                    mip_constr_return.rhs_eq.squeeze().detach().numpy())
                # Now perturb beta by changing some entry from 1 to 0, and vice
                # versa. Now it should not satisfy the constraint.
                perturbed_beta_entry = np.random.randint(0, beta.numel())
                beta_perturbed = beta.clone()
                beta_perturbed[perturbed_beta_entry] =\
                    1 - beta[perturbed_beta_entry]
                lhs_in_perturbed = mip_constr_return.Ain_input @ x_vec +\
                    mip_constr_return.Ain_slack @ z +\
                    mip_constr_return.Ain_slack @ beta_perturbed
                lhs_eq_perturbed = mip_constr_return.Aeq_input @ x_vec +\
                    mip_constr_return.Aeq_slack @ z +\
                    mip_constr_return.Aeq_binary @ beta_perturbed
                self.assertFalse(torch.all(
                    torch.le(
                        lhs_in_perturbed.squeeze(),
                        mip_constr_return.rhs_in.squeeze() +
                        torch.tensor(precision))) and
                    torch.all(torch.le(torch.abs(
                        lhs_eq_perturbed - mip_constr_return.rhs_eq),
                        precision)))
                test_input_output(x)

            # Test with different input x.
            test_input_x(torch.tensor([0.7, 0.2], dtype=self.dtype))
            test_input_x(torch.tensor([-0.3, 0.2], dtype=self.dtype))
            test_input_x(torch.tensor([-0.15, -0.2], dtype=self.dtype))
            test_input_x(torch.tensor([1.1, -0.22], dtype=self.dtype))
            test_input_x(torch.tensor([1.5, -0.8], dtype=self.dtype))
            # The next two input x are outside of [x_lo, x_up]. The constraints
            # should be infeasible.
            test_input_output(torch.tensor([-2., 10.], dtype=self.dtype))
            test_input_output(torch.tensor([-2., 4.], dtype=self.dtype))
            # randomized test
            torch.manual_seed(0)
            np.random.seed(0)
            for _ in range(30):
                found_x = False
                while (not found_x):
                    x_random = torch.tensor(
                        [np.random.normal(0, 1), np.random.normal(0, 1)]).\
                        type(self.dtype)
                    if (torch.all(x_random >= x_lo) and
                            torch.all(x_random <= x_up)):
                        found_x = True
                test_input_x(x_random)

        test_model(self.model1)
        test_model(self.model2)
        test_model(self.model3)
        test_model(self.model4)
        test_model(self.model5)
        test_model(self.model6)
        test_model(self.model7)

    def relu_free_pattern_output_constraint_gradient_tester(self, model):
        # This is the utility function for
        # test_relu_free_pattern_output_constraint_gradient()
        # Test the gradient of the returned argument in
        # ReLUFreePattern.output_constraint. Later we will use this gradient
        # extensively to compute the gradient of the loss w.r.t the network
        # weights/biases, so it is important to make sure that this gradient
        # is correct.
        def compute_loss(*network_parameters):
            param_index = 0
            for layer in model:
                if (isinstance(layer, torch.nn.Linear)):
                    layer.weight = network_parameters[param_index]
                    param_index += 1
                    if (layer.bias is not None):
                        layer.bias = network_parameters[param_index]
                        param_index += 1
            relu_free_pattern = relu_to_optimization.ReLUFreePattern(
                model, self.dtype)
            x_lo = torch.tensor([-1, -2], dtype=self.dtype)
            x_up = torch.tensor([2, 3], dtype=self.dtype)
            mip_constr_return, _, _, _, _ = \
                relu_free_pattern.output_constraint(x_lo, x_up)
            # This function compute the sum of all the return terms. If any of
            # the term has a wrong gradient, the gradient of the sum will also
            # be wrong.
            objective1 = mip_constr_return.Ain_input.sum() +\
                mip_constr_return.Ain_slack.sum() +\
                mip_constr_return.Ain_binary.sum() + \
                mip_constr_return.rhs_in.sum() +\
                mip_constr_return.Aeq_input.sum() +\
                mip_constr_return.Aeq_slack.sum() +\
                mip_constr_return.Aeq_binary.sum() + \
                mip_constr_return.rhs_eq.sum() +\
                mip_constr_return.Aout_slack.sum()
            if isinstance(mip_constr_return.Cout, torch.Tensor):
                objective1 += mip_constr_return.Cout.sum()
            return objective1
            # end of compute_loss

        # Now extract all the parameters in the model
        params_list = []
        for layer in model:
            if isinstance(layer, torch.nn.Linear):
                params_list.append(layer.weight)
                if layer.bias is not None:
                    params_list.append(layer.bias)
        torch.autograd.gradcheck(compute_loss, params_list, atol=1e-6)

    def test_relu_free_pattern_output_constraint_gradient1(self):
        self.relu_free_pattern_output_constraint_gradient_tester(self.model1)

    def test_relu_free_pattern_output_constraint_gradient2(self):
        self.relu_free_pattern_output_constraint_gradient_tester(self.model2)

    def test_relu_free_pattern_output_constraint_gradient3(self):
        self.relu_free_pattern_output_constraint_gradient_tester(self.model3)

    def test_relu_free_pattern_output_constraint_gradient4(self):
        self.relu_free_pattern_output_constraint_gradient_tester(self.model4)

    def test_relu_free_pattern_output_constraint_gradient5(self):
        self.relu_free_pattern_output_constraint_gradient_tester(self.model5)

    def test_relu_free_pattern_output_constraint_gradient6(self):
        self.relu_free_pattern_output_constraint_gradient_tester(self.model6)

    def test_relu_free_pattern_output_constraint_gradient7(self):
        self.relu_free_pattern_output_constraint_gradient_tester(self.model7)

    def test_compute_alpha_index1(self):
        relu_free_pattern = relu_to_optimization.\
            ReLUFreePattern(self.model1, self.dtype)
        self.assertEqual(relu_free_pattern.compute_alpha_index((0, 0, 0)), 0)
        self.assertEqual(relu_free_pattern.compute_alpha_index((0, 1, 0)), 1)
        self.assertEqual(relu_free_pattern.compute_alpha_index((0, 2, 0)), 2)
        self.assertEqual(relu_free_pattern.compute_alpha_index((0, 3, 0)), 3)
        self.assertEqual(relu_free_pattern.compute_alpha_index((1, 0, 0)), 4)
        self.assertEqual(relu_free_pattern.compute_alpha_index((1, 1, 0)), 5)
        self.assertEqual(relu_free_pattern.compute_alpha_index((1, 2, 0)), 6)
        self.assertEqual(relu_free_pattern.compute_alpha_index((1, 3, 0)), 7)
        self.assertEqual(relu_free_pattern.compute_alpha_index((2, 0, 0)), 8)
        self.assertEqual(relu_free_pattern.compute_alpha_index((2, 1, 0)), 9)
        self.assertEqual(relu_free_pattern.compute_alpha_index((2, 2, 0)), 10)
        self.assertEqual(relu_free_pattern.compute_alpha_index((2, 3, 0)), 11)

    def test_compute_alpha_index2(self):
        relu_free_pattern = relu_to_optimization.\
            ReLUFreePattern(self.model2, self.dtype)
        self.assertEqual(relu_free_pattern.compute_alpha_index((0, 0)), 0)
        self.assertEqual(relu_free_pattern.compute_alpha_index((0, 1)), 1)
        self.assertEqual(relu_free_pattern.compute_alpha_index((0, 2)), 2)
        self.assertEqual(relu_free_pattern.compute_alpha_index((0, 3)), 3)
        self.assertEqual(relu_free_pattern.compute_alpha_index((1, 0)), 4)
        self.assertEqual(relu_free_pattern.compute_alpha_index((1, 1)), 5)
        self.assertEqual(relu_free_pattern.compute_alpha_index((1, 2)), 6)
        self.assertEqual(relu_free_pattern.compute_alpha_index((1, 3)), 7)
        self.assertEqual(relu_free_pattern.compute_alpha_index((2, 0)), 8)
        self.assertEqual(relu_free_pattern.compute_alpha_index((2, 1)), 9)
        self.assertEqual(relu_free_pattern.compute_alpha_index((2, 2)), 10)
        self.assertEqual(relu_free_pattern.compute_alpha_index((2, 3)), 11)

    def test_output_gradient(self):
        def test_model(model):
            relu_free_pattern = relu_to_optimization.\
                ReLUFreePattern(model, self.dtype)
            (M, B1, B2, d) = relu_free_pattern.output_gradient()
            num_alpha = 12
            self.assertListEqual(list(M.shape), [num_alpha, 2])

            # Enumerate all the possible activation path, with only one ReLU
            # unit active at each layer. Compute the gradient of the ReLU
            # network network for each activation path through
            # ReLUGivenActivationPattern(), and compare the result aginst M.
            if relu_free_pattern.last_layer_is_relu:
                activation_pattern = [[False, False, False],
                                      [False, False, False, False],
                                      [True]]
            else:
                activation_pattern = [[False, False, False],
                                      [False, False, False, False]]
            precision = 1E-10
            for i0 in range(3):
                activation_pattern[0] = [False, False, False]
                activation_pattern[0][i0] = True
                for i1 in range(4):
                    activation_pattern[1] = [False, False, False, False]
                    activation_pattern[1][i1] = True
                    (g, _, _, _) =\
                        relu_to_optimization.ReLUGivenActivationPattern(
                        model, 2, activation_pattern, self.dtype)
                    if (relu_free_pattern.last_layer_is_relu):
                        alpha_index = relu_free_pattern.compute_alpha_index(
                            (i0, i1, 0))

                    else:
                        alpha_index = relu_free_pattern.compute_alpha_index(
                            (i0, i1))
                    self.assertTrue(
                        torch.all(
                            torch.abs(M[alpha_index] - g.reshape((1, -1)))
                            < precision))
                    alpha_value = torch.zeros((num_alpha, 1), dtype=self.dtype)
                    alpha_value[alpha_index][0] = 1.
                    beta_value = torch.zeros((relu_free_pattern.num_relu_units,
                                              1), dtype=self.dtype)
                    beta_value[relu_free_pattern.relu_unit_index[0][i0]][0] =\
                        1.
                    beta_value[relu_free_pattern.relu_unit_index[1][i1]][0] =\
                        1.
                    if (relu_free_pattern.last_layer_is_relu):
                        beta_value[relu_free_pattern.relu_unit_index[2][0]
                                   ][0] = 1.
                    self.assertTrue(
                        torch.all(B1 @ alpha_value + B2 @ beta_value - d <
                                  precision))
                    # Now perturb alpha value a bit, by negating a value from 1
                    # to 0 or vice versa, the perturbed alpha and beta should
                    # violate the constraint.
                    perturbed_alpha_entry = np.random.randint(
                        0, alpha_value.numel())
                    alpha_value[perturbed_alpha_entry] = 1. - \
                        alpha_value[perturbed_alpha_entry]
                    self.assertFalse(
                        torch.all(B1 @ alpha_value + B2 @ beta_value - d <
                                  precision))

        test_model(self.model1)
        test_model(self.model2)

    def test_output_gradient_times_vector(self):
        def test_model(model, x, y, y_lo, y_up):
            assert(x.shape == (2, ))
            assert(y.shape == (2, ))
            assert(y_lo.shape == (2, ))
            assert(y_up.shape == (2, ))
            assert(torch.all(y <= y_up) and torch.all(y >= y_lo))
            activation_pattern =\
                relu_to_optimization.ComputeReLUActivationPattern(model, x)
            relu_free_pattern = relu_to_optimization.ReLUFreePattern(
                model, self.dtype)
            beta = torch.empty((relu_free_pattern.num_relu_units,),
                               dtype=self.dtype)
            for layer in range(len(relu_free_pattern.relu_unit_index)):
                for index, beta_index in enumerate(
                        relu_free_pattern.relu_unit_index[layer]):
                    beta[beta_index] = 1. if activation_pattern[layer][index]\
                        else 0.
            (g, _, _, _) = relu_to_optimization.ReLUGivenActivationPattern(
                model, 2, activation_pattern, self.dtype)
            output_expected = g.squeeze() @ y
            (a_out, A_y, A_z, A_beta, rhs, z_lo, z_up) =\
                relu_free_pattern.output_gradient_times_vector(
                    y_lo, y_up)

            # Now compute z manually
            z_expected = torch.empty((relu_free_pattern.num_relu_units),
                                     dtype=self.dtype)
            z_pre = y
            layer_count = 0
            for layer in model:
                if (isinstance(layer, nn.Linear)):
                    z_cur = layer.weight.data @ z_pre
                elif isinstance(layer, nn.ReLU) or \
                        isinstance(layer, nn.LeakyReLU):
                    if isinstance(layer, nn.ReLU):
                        z_cur = beta[relu_free_pattern.relu_unit_index[
                            layer_count]] * z_cur
                    else:
                        for i in range(len(relu_free_pattern.relu_unit_index[
                                layer_count])):
                            if activation_pattern[layer_count][i]:
                                z_cur[i] = z_cur[i]
                            else:
                                z_cur[i] = layer.negative_slope * z_cur[i]
                    z_expected[relu_free_pattern.relu_unit_index[layer_count]]\
                        = z_cur
                    z_pre = z_cur
                    layer_count += 1

            # Now check that z_expected is within the bound.
            np.testing.assert_array_less(z_expected.detach().numpy(),
                                         z_up.detach().numpy() + 1E-10)
            np.testing.assert_array_less(z_lo.detach().numpy() - 1E-10,
                                         z_expected.detach().numpy())
            # Check that the output equals to a_out.dot(z_expected)
            self.assertAlmostEqual((a_out @ z_expected).item(),
                                   output_expected.item())
            # Check that y, z, beta satisfies the constraint
            lhs = A_y @ y + A_z @ z_expected + A_beta @ beta
            np.testing.assert_array_less(lhs.detach().numpy(),
                                         rhs.detach().numpy() + 1E-10)

            # Now solve an optimization problem satisfying the constraint, and
            # fix y and beta. The only z that satisfies the constraint should
            # be z_expected.
            z_var = cp.Variable(relu_free_pattern.num_relu_units)
            objective = cp.Minimize(0.)
            con = [A_z.detach().numpy() @ z_var <=
                   (rhs - A_y @ y - A_beta @ beta).detach().numpy()]
            prob = cp.Problem(objective, con)
            prob.solve(solver=cp.GUROBI)
            np.testing.assert_array_almost_equal(
                z_var.value, z_expected.detach().numpy())

        # Check for different models and inputs.
        for model in (self.model1, self.model2, self.model3, self.model4,
                      self.model5):
            test_model(model, torch.tensor([1.5, 2.], dtype=self.dtype),
                       torch.tensor([0., 0.], dtype=self.dtype),
                       torch.tensor([-1., -2.], dtype=self.dtype),
                       torch.tensor([20., 3.], dtype=self.dtype))
            test_model(model, torch.tensor([2., 3.], dtype=self.dtype),
                       torch.tensor([1., 2.], dtype=self.dtype),
                       torch.tensor([-1., 0.], dtype=self.dtype),
                       torch.tensor([2., 3.], dtype=self.dtype))
            test_model(model, torch.tensor([2.,  -1.], dtype=self.dtype),
                       torch.tensor([1., 2.], dtype=self.dtype),
                       torch.tensor([-1., 0.], dtype=self.dtype),
                       torch.tensor([2., 3.], dtype=self.dtype))
            test_model(model, torch.tensor([-2.,  -1.], dtype=self.dtype),
                       torch.tensor([1., 2.], dtype=self.dtype),
                       torch.tensor([-1., 1.], dtype=self.dtype),
                       torch.tensor([2., 3.], dtype=self.dtype))
            test_model(model, torch.tensor([-4.,  -2.], dtype=self.dtype),
                       torch.tensor([1.5, -2.], dtype=self.dtype),
                       torch.tensor([-1., -4.], dtype=self.dtype),
                       torch.tensor([2., 3.], dtype=self.dtype))
            test_model(model, torch.tensor([-4.,  2.5], dtype=self.dtype),
                       torch.tensor([2.5, -2.], dtype=self.dtype),
                       torch.tensor([-1., -4.], dtype=self.dtype),
                       torch.tensor([4., 3.], dtype=self.dtype))
        # randomized test.
        torch.manual_seed(0)
        np.random.seed(0)
        for _ in range(30):
            found_y_bound = False
            while (not found_y_bound):
                y_lo = torch.tensor([-1 + np.random.normal(0, 1),
                                     1. + np.random.normal(0, 1)],
                                    dtype=self.dtype)
                y_up = torch.tensor([2 + np.random.normal(0, 1),
                                     3. + np.random.normal(0, 1)],
                                    dtype=self.dtype)
                if torch.all(y_up > y_lo):
                    found_y_bound = True
            y = torch.tensor([np.random.uniform(y_lo[0], y_up[0]),
                              np.random.uniform(y_lo[1], y_up[1])],
                             dtype=self.dtype)
            x = torch.from_numpy(np.random.normal(0, 1, (2,))).type(self.dtype)
            test_model(self.model1, x, y, y_lo, y_up)
            test_model(self.model2, x, y, y_lo, y_up)


if __name__ == "__main__":
    unittest.main()