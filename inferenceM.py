import torch
import numpy as np
import sys
import os
import torch.nn as nn
import torch.nn.functional as F
import yaml
import pickle
from model import AE
from utils import *
from functools import reduce
import json
from collections import defaultdict
from torch.utils.data import Dataset
from torch.utils.data import TensorDataset
from torch.utils.data import DataLoader
from argparse import ArgumentParser, Namespace
from scipy.io.wavfile import write
import random
from preprocess.tacotron.utils import melspectrogram2wav
from preprocess.tacotron.utils import get_spectrograms
import librosa
import shutil

class Inferencer(object):
    def __init__(self, config, args):
        # config store the value of hyperparameters, turn to attr by AttrDict
        self.config = config
        print(config)
        # args store other information
        self.args = args
        print(self.args)

        # init the model with config
        self.build_model()

        # load model
        self.load_model()

        with open(self.args.attr, 'rb') as f:
            self.attr = pickle.load(f)

    def load_model(self):
        print(f'Load model from {self.args.model}')
        self.model.load_state_dict(torch.load(self.args.model, map_location=torch.device('cpu'), weights_only=True))
        return

    def build_model(self): 
        # create model, discriminator, optimizers
        self.model = cc(AE(self.config))
        self.model.to(torch.device('cpu'))  # Ensure model is on CPU
        print(self.model)
        self.model.eval()
        return

    def utt_make_frames(self, x):
        frame_size = self.config['data_loader']['frame_size']
        remains = x.size(0) % frame_size 
        if remains != 0:
            x = F.pad(x, (0, remains))
        out = x.view(1, x.size(0) // frame_size, frame_size * x.size(1)).transpose(1, 2)
        return out

    def inference_one_utterance(self, x, x_cond):
        x = self.utt_make_frames(x)
        x_cond = self.utt_make_frames(x_cond)
        dec = self.model.inference(x, x_cond)
        dec = dec.transpose(1, 2).squeeze(0)
        dec = dec.detach().cpu().numpy()
        dec = self.denormalize(dec)
        wav_data = melspectrogram2wav(dec)
        return wav_data, dec

    def denormalize(self, x):
        m, s = self.attr['mean'], self.attr['std']
        ret = x * s + m
        return ret

    def normalize(self, x):
        m, s = self.attr['mean'], self.attr['std']
        ret = (x - m) / s
        return ret

    def write_wav_to_file(self, wav_data, output_path):
        write(output_path, rate=self.args.sample_rate, data=wav_data)
        return

    def create_test_folder(self):
        base_dir = "test_files"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        
        test_folder_num = 1
        while os.path.exists(os.path.join(base_dir, f"test{test_folder_num}")):
            test_folder_num += 1
        
        test_folder_path = os.path.join(base_dir, f"test{test_folder_num}")
        os.makedirs(test_folder_path)
        return test_folder_path

    def save_files(self, test_folder, src_path, target_path, output_path, target_num):
        shutil.copy2(src_path, os.path.join(test_folder, "source.wav"))
        shutil.copy2(target_path, os.path.join(test_folder, f"target{target_num}.wav"))
        shutil.copy2(output_path, os.path.join(test_folder, f"output{target_num}.wav"))

    def inference_from_path(self):
        src_mel, _ = get_spectrograms(self.args.source)
        device = torch.device('cpu')  # Ensure device is set to CPU
        src_mel = torch.from_numpy(self.normalize(src_mel)).to(device)

        target_paths = [self.args.target1, self.args.target2, self.args.target3]
        output_paths = [self.args.output1, self.args.output2, self.args.output3]

        test_folder = self.create_test_folder()

        for i, (target_path, output_path) in enumerate(zip(target_paths, output_paths), start=1):
            tar_mel, _ = get_spectrograms(target_path)
            tar_mel = torch.from_numpy(self.normalize(tar_mel)).to(device)
            conv_wav, conv_mel = self.inference_one_utterance(src_mel, tar_mel)
            self.write_wav_to_file(conv_wav, output_path)
            self.save_files(test_folder, self.args.source, target_path, output_path, i)
        return


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-attr', '-a', help='attr file path')
    parser.add_argument('-config', '-c', help='config file path')
    parser.add_argument('-model', '-m', help='model path')
    parser.add_argument('-source', '-s', help='source wav path')
    parser.add_argument('-target1', '-t1', help='target1 wav path')
    parser.add_argument('-target2', '-t2', help='target2 wav path')
    parser.add_argument('-target3', '-t3', help='target3 wav path')
    parser.add_argument('-output1', '-o1', help='output1 wav path')
    parser.add_argument('-output2', '-o2', help='output2 wav path')
    parser.add_argument('-output3', '-o3', help='output3 wav path')
    parser.add_argument('-sample_rate', '-sr', help='sample rate', default=24000, type=int)
    args = parser.parse_args()
    # load config file 
    with open(args.config) as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    inferencer = Inferencer(config=config, args=args)
    inferencer.inference_from_path()
