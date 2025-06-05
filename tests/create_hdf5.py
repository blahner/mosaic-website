from dotenv import load_dotenv
load_dotenv()
import os
import argparse
import h5py
import numpy as np
import glob
from pathlib import Path
import pandas as pd
from tqdm import tqdm

"""
Generate a fake hdf5 file with all the required attributes to test uploads.
"""

def main(args):
    short_to_long = {"hw": "helloworld"}
    visual_angles = {"hw": 5}
    publications = {"hw": "https://www.nature.com/"}
    githubs = {"hw": "github.com"}
    groups = ["sub-01_hw"]
    # Create a file
    print("starting hdf5 file creation...")
    for group in tqdm(groups, total=len(groups), desc="Adding 'sub-XX_DATASET' groups to hdf5 file"):
        with h5py.File(os.path.join(args.save_root, "tests", f'{group}.hdf5'), 'w') as grp:
            print(f"Working on group: {group}")
            subject, fmri_dataset_name = group.split('_')
            grp.attrs.create("visual_angle", visual_angles[fmri_dataset_name])
            grp.attrs.create('sex', 'male')
            grp.attrs.create('age', 30)
            grp.attrs.create('publication_url', publications[fmri_dataset_name])
            grp.attrs.create('github_url', githubs[fmri_dataset_name])
            grp.attrs.create('owner_name', "John Smith")
            grp.attrs.create('owner_email', "jsmith@email.com")
            grp.attrs.create('dataset_name', short_to_long[fmri_dataset_name])
            grp.attrs.create('sub-ID', subject)
            grp.attrs.create('pipeline', "fMRIPrepv23.2.0")
            grp.attrs.create('trial_format', "betas")
                             
            grp_noiseceiling = grp.create_group(f"noiseceilings", track_order=True)
            n = '1'
            phase = 'train'
            dset = grp_noiseceiling.create_dataset('dummy', data=np.zeros((91282,)), track_order=True)
            dset.attrs.create('nan_indices', np.zeros((1000,))) #arbitrary number of nans
            dset.attrs.create('n', n)
            dset.attrs.create('phase', phase)
            
            grp_betas = grp.create_group(f"betas", track_order=True)
            phase = 'train'
            stimulus_name = 'dummy_stimulus_name'
            rep = '1'

            dset = grp_betas.create_dataset('dummy_betas', data=np.zeros((91282,)), track_order=True)
            dset.attrs.create('nan_indices', np.zeros((1000,)))
            dset.attrs.create('phase', phase)
            dset.attrs.create('repetition', rep)
            dset.attrs.create('presented_stimulus_filename', stimulus_name)
            dset.attrs.create('image_stimulus_filename', stimulus_name)

if __name__=='__main__':
    save_root_default = os.path.join(os.getenv("PROJECT_ROOT", "/default/path/to/project"), "mosaic-website") #use default if DATASETS_ROOT env variable is not set.

    parser = argparse.ArgumentParser()
    parser.add_argument("--save_root", type=str, default=save_root_default, help="Root path to scratch datasets folder.")

    args = parser.parse_args()
    
    main(args)