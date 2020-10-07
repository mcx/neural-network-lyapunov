import os
import torch
import numpy as np
import pybullet_data as pbd
import neural_network_lyapunov


def urdf_path(file):
    return os.path.join(os.path.dirname(neural_network_lyapunov.__file__),
                        "urdf", file)


def load_falling_cubes_callback():
    def cb(pb):
        plane_id = pb.loadURDF(urdf_path("plane_white.urdf"))
        pos = [0, 0, .25]
        orn = pb.getQuaternionFromEuler([0, 0, 0])
        cube1_id = pb.loadURDF(urdf_path("cube_blue.urdf"), pos, orn)
        pos = [0.03, 0, 0.025]
        cube2_id = pb.loadURDF(urdf_path("cube_red.urdf"), pos, orn)
        pos = [-.075, 0, 0.025]
        cube3_id = pb.loadURDF(urdf_path("cube_red.urdf"), pos, orn)
        return cube1_id
    return cb


def load_cluttered_table_callback():
    def cb(pb):
        flags = pb.URDF_ENABLE_CACHED_GRAPHICS_SHAPES & \
            pb.URDF_USE_SELF_COLLISION & \
            pb.URDF_USE_INERTIA_FROM_FILE
        table_height = .625

        pb.setAdditionalSearchPath(pbd.getDataPath())

        table_id = pb.loadURDF("table_square/table_square.urdf")

        pos = [0.04, 0.04, table_height]
        orn = [0.42, 0.56, 0.56, 0.43]
        duck_id = pb.loadURDF("duck_vhacd.urdf", pos, orn)

        pos = [0.01, -.1, 0.009 + table_height]
        orn = pb.getQuaternionFromEuler([0, 0, np.pi/4])
        block4_id = pb.loadURDF(urdf_path("block_green.urdf"), pos, orn)

        pos = [-.07, 0, 0.025 + table_height]
        orn = pb.getQuaternionFromEuler([0, 0, 0])
        cube_red = pb.loadURDF(
            urdf_path("cube_pink.urdf"), pos, orn, flags=flags)

        pos = [1, 1, .25 + table_height]
        orn = pb.getQuaternionFromEuler([0, 0, 0])
        cube_blue = pb.loadURDF(urdf_path("cubes_numbers/cube_0.urdf"),
                                pos, orn, flags=flags)

        return cube_blue
    return cb