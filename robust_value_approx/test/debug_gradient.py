import torch
import gurobipy
import numpy as np

import robust_value_approx.lyapunov as lyapunov
import robust_value_approx.utils as utils
import robust_value_approx.test.test_hybrid_linear_system as \
    test_hybrid_linear_system
import robust_value_approx.test.train_continuous_linear_system_toy_lyapunov as\
    train_continuous_linear_system_toy_lyapunov
import robust_value_approx.test.train_2d_lyapunov_utils as\
    train_2d_lyapunov_utils
import robust_value_approx.train_lyapunov as train_lyapunov

import argparse


def compute_total_loss(
    system, x_equilibrium, relu_layer_width, params_val, V_rho,
    lyapunov_positivity_epsilon, lyapunov_derivative_epsilon, state_samples,
        state_samples_next, bias, requires_grad):
    dut = train_lyapunov.TrainLyapunovReLU(
        lyapunov.LyapunovContinuousTimeHybridSystem(system), V_rho,
        x_equilibrium)
    dut.lyapunov_derivative_sample_cost_weight = 0.
    dut.lyapunov_positivity_sample_cost_weight = 0.
    dut.lyapunov_derivative_mip_cost_weight = 1.
    dut.lyapunov_positivity_mip_cost_weight = 10.
    dut.lyapunov_derivative_mip_pool_solutions = 1
    dut.lyapunov_positivity_mip_pool_solutions = 1
    dut.lyapunov_positivity_epsilon = lyapunov_positivity_epsilon
    dut.lyapunov_derivative_epsilon = lyapunov_derivative_epsilon
    relu = train_continuous_linear_system_toy_lyapunov.setup_relu(
        relu_layer_width, params_val, bias=bias)
    total_loss = dut.total_loss(relu, state_samples, state_samples_next)
    if requires_grad:
        total_loss[0].backward()
        grad = np.concatenate(
            [p.grad.detach().numpy().reshape((-1,)) for p in
             relu.parameters()], axis=0)
        return grad
    else:
        return total_loss[0].item()


def compute_milp_cost_given_relu(
    system, x_equilibrium, relu_layer_width, params_val, V_rho,
    lyapunov_positivity_epsilon, lyapunov_derivative_epsilon, bias,
        requires_grad, positivity_milp):
    relu = train_continuous_linear_system_toy_lyapunov.setup_relu(
        relu_layer_width, params_val, bias=bias)
    dut = lyapunov.LyapunovContinuousTimeHybridSystem(system)
    if positivity_milp:
        milp = dut.lyapunov_positivity_as_milp(
            relu, x_equilibrium, V_rho, lyapunov_positivity_epsilon)[0]
    else:
        milp = dut.lyapunov_derivative_as_milp(
            relu, x_equilibrium, V_rho, lyapunov_derivative_epsilon,
            None, None)[0]
    milp.gurobi_model.setParam(gurobipy.GRB.Param.OutputFlag, False)
    milp.gurobi_model.optimize()
    objective = milp.compute_objective_from_mip_data_and_solution(
        penalty=1e-13)
    print(objective.item())
    if requires_grad:
        objective.backward()
        grad = np.concatenate(
            [p.grad.detach().numpy().reshape((-1,)) for p in
             relu.parameters()], axis=0)
        return grad
    else:
        return objective.item()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--system", type=int, help="johansson system index")
    parser.add_argument(
        "--relu", type=str, help="relu model pickle file.")
    parser.add_argument(
        "--function", type=str, help="positivity, derivative or loss")
    parser.add_argument(
        "--bias", help="use bias in linear layer.", action="store_true")
    args = parser.parse_args()
    if args.system == 1:
        system = test_hybrid_linear_system.\
            setup_johansson_continuous_time_system1()
    elif args.system == 2:
        system = test_hybrid_linear_system.\
            setup_johansson_continuous_time_system2()
    elif args.system == 3:
        system = test_hybrid_linear_system.\
            setup_johansson_continuous_time_system3(
                torch.tensor([0, 0], dtype=torch.float64))
    elif args.system == 4:
        system = test_hybrid_linear_system.\
            setup_johansson_continuous_time_system4()

    x_equilibrium = torch.tensor([0., 0.], dtype=system.dtype)
    relu = torch.load(args.relu)
    relu_layer_width = [None] * int((len(relu) + 1)/2)
    for i in range(int((len(relu) + 1) / 2)):
        relu_layer_width[i] = relu[2 * i].in_features
    relu_layer_width = tuple(relu_layer_width)
    relu_params_val = torch.cat(tuple(
        param.reshape((-1,)) for param in relu.parameters())).detach()
    V_rho = 0.
    lyapunov_positivity_epsilon = 0.01
    lyapunov_derivative_epsilon = 0.01
    state_samples = train_2d_lyapunov_utils.setup_state_samples_all(
        x_equilibrium, torch.tensor([-1, -1], dtype=torch.float64),
        torch.tensor([1, 1], dtype=torch.float64), (15, 15), 0.)
    state_samples_next = torch.stack([
        system.step_forward(state_samples[i]) for i in
        range(state_samples.shape[0])], dim=0)

    if args.function == "positivity" or args.function == "derivative":
        grad = compute_milp_cost_given_relu(
            system, x_equilibrium, relu_layer_width, relu_params_val, V_rho,
            lyapunov_positivity_epsilon, lyapunov_derivative_epsilon,
            args.bias, True, args.function == "positivity")
        grad_numerical = utils.compute_numerical_gradient(
            lambda p: compute_milp_cost_given_relu(
                system, x_equilibrium, relu_layer_width, torch.from_numpy(p),
                V_rho, lyapunov_positivity_epsilon,
                lyapunov_derivative_epsilon, args.bias, False,
                args.function == "positivity"), relu_params_val, dx=1e-8)
    elif args.function == "loss":
        grad = compute_total_loss(
            system, x_equilibrium, relu_layer_width, relu_params_val, V_rho,
            lyapunov_positivity_epsilon, lyapunov_derivative_epsilon,
            state_samples, state_samples_next, args.bias, True)
        grad_numerical = utils.compute_numerical_gradient(
            lambda p: compute_total_loss(
                system, x_equilibrium, relu_layer_width, torch.from_numpy(p),
                V_rho, lyapunov_positivity_epsilon,
                lyapunov_derivative_epsilon, state_samples, state_samples_next,
                args.bias, False),
            relu_params_val, dx=1e-8)
    print(grad)
    print(grad_numerical)
    print(grad - grad_numerical)
    np.testing.assert_allclose(grad, grad_numerical)