#!/usr/bin/env python3

import argparse
import pickle
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description='Export an accumulated Cartographer point cloud pickle to a CloudCompare-readable PLY file.'
    )
    parser.add_argument(
        'input',
        nargs='?',
        default='maps/agv_house_cartographer_3d_pointcloud_accumulated.pkl',
        help='Input .pkl file produced by accumulate_pointcloud_map.py',
    )
    parser.add_argument(
        'output',
        nargs='?',
        default='maps/agv_house_cartographer_3d_pointcloud_accumulated.ply',
        help='Output .ply file for CloudCompare',
    )
    return parser.parse_args()


def load_voxels(path: Path):
    with path.open('rb') as handle:
        state = pickle.load(handle)
    voxels = state.get('voxels')
    if not isinstance(voxels, dict):
        raise ValueError(f'{path} does not contain a valid "voxels" dictionary')
    return voxels


def write_ply(path: Path, voxels):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='ascii') as handle:
        handle.write('ply\n')
        handle.write('format ascii 1.0\n')
        handle.write('comment exported from agv_ros accumulated point cloud pickle\n')
        handle.write(f'element vertex {len(voxels)}\n')
        handle.write('property float x\n')
        handle.write('property float y\n')
        handle.write('property float z\n')
        handle.write('property float intensity\n')
        handle.write('property int count\n')
        handle.write('end_header\n')
        for x, y, z, intensity, count in voxels.values():
            handle.write(f'{x:.6f} {y:.6f} {z:.6f} {intensity:.6f} {int(count)}\n')


def main():
    args = parse_args()
    input_path = Path(args.input).expanduser()
    output_path = Path(args.output).expanduser()
    voxels = load_voxels(input_path)
    write_ply(output_path, voxels)
    print(f'Exported {len(voxels)} points to {output_path}')


if __name__ == '__main__':
    main()
