import os
import numpy as np
import pickle as pk
from torch.utils.data import Dataset

import pickle as pk
import numpy as np
import torch
import os

actions = [
    'hammer.pkl',
    'lift.pkl',
    'place-hp.pkl',
    'place-lp.pkl',
    'polish.pkl',
    'span_heavy.pkl',
    'span_light.pkl',
    'place-hp_CRASH.pkl',
    'place-lp_CRASH.pkl',
    'polish_CRASH.pkl',
    'span_heavy_CRASH.pkl',
    'span_light_CRASH.pkl'
]

normal_actions = [
    'hammer.pkl',
    'lift.pkl',
    'place-hp.pkl',
    'place-lp.pkl',
    'polish.pkl',
    'span_heavy.pkl',
    'span_light.pkl'
]

abnormal_actions = [
    'place-hp_CRASH.pkl',
    'place-lp_CRASH.pkl',
    'polish_CRASH.pkl',
    'span_heavy_CRASH.pkl',
    'span_light_CRASH.pkl'
]

abnormal_actions_ = [
    'place-hp_CRASH',
    'place-lp_CRASH',
    'polish_CRASH',
    'span_heavy_CRASH',
    'span_light_CRASH'
]

normal_actions_ = [
    'hammer',
    'lift',
    'place-hp',
    'place-lp',
    'polish',
    'span_heavy',
    'span_light'
]


def p_down(mydata, Index):
    '''
    leng, features, seq_len
    '''
    leng, features, seq_len = mydata.shape
    mydata = mydata.reshape(leng, -1, 3, seq_len)  # x, 22, 3, 35

    da = np.zeros((leng, len(Index), 3, seq_len)) # x, 12, 3, 35
    for i in range(len(Index)):
        da[:, i, :, :] = np.mean(mydata[:, Index[i], :, :], axis=1)
    da = da.reshape(leng, -1, seq_len)
    return da

def downs_from_22(downs, down_key):

    for key1, key2, key3 in down_key:
        downs[key2] = p_down(downs[key1], key3)
    return downs


def get_dct_matrix(N):
    dct_m = np.eye(N)
    for k in np.arange(N):
        for i in np.arange(N):
            w = np.sqrt(2 / N)
            if k == 0:
                w = np.sqrt(1 / N)
            dct_m[k, i] = w * np.cos(np.pi * (i + 1 / 2) * k / N)
    idct_m = np.linalg.inv(dct_m)
    return dct_m, idct_m

def dct_transform_numpy(data, dct_m, dct_n):
    '''
    B, 60, 35
    '''
    batch_size, features, seq_len = data.shape
    data = data.reshape(-1, seq_len)  # [180077*60， 35]
    data = data.transpose(1, 0)  # [35, b*60]

    out_data = np.matmul(dct_m[:dct_n, :], data)  # [dct_n, 180077*60]
    out_data = out_data.transpose().reshape((-1, features, dct_n))  # [b, 60, dct_n]
    return out_data

def reverse_dct_numpy(dct_data, idct_m, seq_len):
    '''
    B, 60, 35
    '''
    batch_size, features, dct_n = dct_data.shape

    dct_data = dct_data.transpose(2, 0, 1).reshape((dct_n, -1))  # dct_n, B*60
    out_data = np.matmul(idct_m[:, :dct_n], dct_data).reshape((seq_len, batch_size, -1)).transpose(1, 2, 0)
    return out_data

def dct_transform_torch(data, dct_m, dct_n):
    '''
    B, 60, 35
    '''
    batch_size, features, seq_len = data.shape

    data = data.contiguous().view(-1, seq_len)  # [180077*60， 35]
    data = data.permute(1, 0)  # [35, b*60]

    out_data = torch.matmul(dct_m[:dct_n, :], data)  # [dct_n, 180077*60]
    out_data = out_data.permute(1, 0).contiguous().view(-1, features, dct_n)  # [b, 60, dct_n]
    return out_data

def reverse_dct_torch(dct_data, idct_m, seq_len):
    '''
    B, 60, 35
    '''
    batch_size, features, dct_n = dct_data.shape

    dct_data = dct_data.permute(2, 0, 1).contiguous().view(dct_n, -1)  # dct_n, B*60
    out_data = torch.matmul(idct_m[:, :dct_n], dct_data).contiguous().view(seq_len, batch_size, -1).permute(1, 2, 0)
    return out_data

class PoseDataset(Dataset):
    def __init__(self, 
                 data_path,
                 split='train',
                 input_time_frames=10,
                 output_time_frames=25,
                 win_stride=0, collision=False,
                 actions=None):
        super(PoseDataset).__init__()
        
        self.data_path = data_path
        self.split = split
        self.in_tf = input_time_frames
        self.out_tf = output_time_frames
        self.win_size = input_time_frames + output_time_frames
        self.win_stride = self.win_size if win_stride == 0 else win_stride
        
        if split == 'train':
            self.subjects =  [
                'S05', 'S06', 'S07', 'S08',
                'S09', 'S10', 'S11', 'S12', 
                'S13', 'S14', 'S15','S01', 
                'S16', 'S17'
            ]
            
            if collision == False:
                self.allowed_actions = {'file': normal_actions,
                                        'acts': normal_actions_}
            else:
                self.allowed_actions = {'file': abnormal_actions,
                                        'acts': abnormal_actions_}
        elif split == 'validation':
            
            self.subjects = ['S00','S04']
            if collision == False:
                self.allowed_actions = {'file': normal_actions,
                                        'acts': normal_actions_}
            else:
                self.allowed_actions = {'file': abnormal_actions,
                                        'acts': abnormal_actions_}
        elif split == 'test':
            self.subjects = ['S02', 'S03', 'S18', 'S19']
            
            if collision == False:
                self.allowed_actions = {'file': normal_actions,
                                        'acts': normal_actions_}
            else:
                self.allowed_actions = {'file': abnormal_actions,
                                        'acts': abnormal_actions_}
        else:
            self.subjects = None        
    
        self.actions = []
        
        for act in actions:
            if act.endswith('.pkl'):
                if act in self.allowed_actions['file']:
                    self.actions.append(act)
            else:
                if act in self.allowed_actions['acts']:
                    self.actions.append(act + '.pkl')
                    
        assert self.actions != [], 'there should be at least one action'
                
        self.windows = self.build_dataset()
        
        
    def __getitem__(self, index):
        return self.windows[index]
    
    def __len__(self):
        return self.windows.shape[0]
        
    def build_dataset(self):
        
        all_data = []        
        
        for subject in self.subjects:
            sub_path = os.path.join(self.data_path, subject)
            sub_actions_paths = [os.path.join(sub_path, act) for act in os.listdir(sub_path) if ((act.endswith('.pkl')) & (act in self.actions))]
            for sub_actions_path in sub_actions_paths:
                data = self.retrieve_data(sub_actions_path)
                splitted_windows = self.split_single_pose(data)
                all_data.append(splitted_windows)
        
        return np.concatenate(all_data)
    
    def retrieve_data(self, action_path):
        with open(action_path, 'rb') as f:
            all_data = pk.load(f)
        
        human_related_data = [x[0] for x in all_data]
        
        single_hpose_np = np.stack(human_related_data, axis=0)
        
        return single_hpose_np
    
    def split_single_pose(self, single_pose_array):
        T, _, _ = single_pose_array.shape
        
        iterations = np.ceil((T-self.win_size)/self.win_stride).astype(int)+1
        all_windows = []
        for segment in range(iterations):
            start_index = self.win_stride * segment
            end_index = start_index + self.win_size
            
            curr_win = single_pose_array[start_index:end_index]
            if curr_win.shape[0] == (self.in_tf + self.out_tf):
                all_windows.append(curr_win)
        
        return np.stack(all_windows, axis=0)
    
    
class PoseDatasetMSR(Dataset):
    def __init__(self, 
                 data_path='safeHR',
                 split='train',
                 input_time_frames=10,
                 output_time_frames=25,
                 win_stride=0,
                 actions=None,
                 dct_used=15,
                 global_min=0,
                 global_max=0,
                 debug_step=100):
        super(PoseDataset).__init__()
        
        self.data_path = data_path
        self.split = split
        self.in_tf = input_time_frames
        self.out_tf = output_time_frames
        self.win_size = input_time_frames + output_time_frames
        self.win_stride = self.win_size if win_stride == 0 else win_stride
        
        if split == 'train':
            self.subjects = ['S02', 'S03', 'S04', 'S05', 'S06', 'S08']
        elif split == 'validation':
            self.subjects = ['S07']
        elif split == 'test':
            self.subjects = ['S01']
        else:
            self.subjects = None

        self.allowed_actions = {'file': normal_actions,
                                'acts': normal_actions_}
        self.actions = []
        
        for act in actions:
            if act.endswith('.pkl'):
                if act in self.allowed_actions['file']:
                    self.actions.append(act)
            else:
                if act in self.allowed_actions['acts']:
                    self.actions.append(act + '.pkl')
                    
        assert self.actions != [], 'there should be at least one action'
                
        self.windows = self.build_dataset()
        
        self.Index1714 = [[0, 9], 
                          [1], [2], [3], ##r_leg
                          [4], [5], [6], # l_leg
                          [7, 8, 10], #head
                          [11], [12], [13], #l_arm
                          [14], [15], [16]] #r_arm
        
        self.Index149 = [[0, 7], #head-body
                         [1, 2], [2, 3], #r_leg
                         [4, 5], [5, 6], #l_leg
                         [8, 9], [9, 10], #l_arm
                         [11, 12], [12, 13]] #r_arm
        
        self.Index94 = [[0, 1, 2], #down_right 
                        [0, 3, 4], #down_left
                        [0, 5, 6], #upper_left
                        [0, 7, 8]] #upper_right
        
        self.down_key=[('p17', 'p14', self.Index1714),
                       ('p14', 'p9', self.Index149),
                       ('p9', 'p4', self.Index94)]
        
        S, T, V, D = self.windows.shape
        gt_17 = self.windows.transpose(0, 2, 3, 1)
        gt_17 = gt_17.reshape(S, D*V, T)
        
        gt_all_scales = {'p17': gt_17}
        gt_all_scales = downs_from_22(gt_all_scales, down_key=self.down_key)
        
        input_all_scales = {}
        for k in gt_all_scales.keys():
            input_all_scales[k] = np.concatenate((gt_all_scales[k][:, :, :self.in_tf], np.repeat(gt_all_scales[k][:, :, self.in_tf-1:self.in_tf], self.out_tf, axis=-1)), axis=-1)
        
        self.dct_used = dct_used
        self.dct_m, self.idct_m = get_dct_matrix(self.win_size)

        for k in input_all_scales:
            input_all_scales[k] = dct_transform_numpy(input_all_scales[k], self.dct_m, dct_used)

        # Max min norm to -1 -> 1 ***********
        self.global_max = global_max
        self.global_min = global_min

        if split == 'train':
            gt_max = []
            gt_min = []
            for k in gt_all_scales.keys():
                gt_max.append(np.max(gt_all_scales[k]))
                gt_min.append(np.min(gt_all_scales[k]))
            for k in input_all_scales.keys():
                gt_max.append(np.max(input_all_scales[k]))
                gt_min.append(np.min(input_all_scales[k]))

            self.global_max = np.max(np.array(gt_max))
            self.global_min = np.min(np.array(gt_min))

        for k in input_all_scales.keys():
            input_all_scales[k] = (input_all_scales[k] - self.global_min) / (self.global_max - self.global_min)
            input_all_scales[k] = input_all_scales[k] * 2 - 1

        little = np.arange(0, input_all_scales[list(input_all_scales.keys())[0]].shape[0], debug_step)
        for k in input_all_scales:
            input_all_scales[k] = input_all_scales[k][little]
            gt_all_scales[k] = gt_all_scales[k][little]

        self.gt_all_scales = gt_all_scales
        self.input_all_scales = input_all_scales
        
    def __getitem__(self, index):
        gts = {}
        inputs = {}
        for k in ['p17', 'p14', 'p9', 'p4']:
            gts[k] = self.gt_all_scales[k][index]
            inputs[k] = self.input_all_scales[k][index]
        
        return inputs, gts
    
    def __len__(self):
        return self.gt_all_scales[list(self.gt_all_scales.keys())[0]].shape[0]
        
    def build_dataset(self):
        
        all_data = []        
        
        for subject in self.subjects:
            sub_path = os.path.join(self.data_path, subject)
            sub_actions_paths = [os.path.join(sub_path, act) for act in os.listdir(sub_path) if ((act.endswith('.pkl')) & (act in self.actions))]
            for sub_actions_path in sub_actions_paths:
                data = self.retrieve_data(sub_actions_path)
                splitted_windows = self.split_single_pose(data)
                all_data.append(splitted_windows)
        
        return np.concatenate(all_data)
    
    def retrieve_data(self, action_path):
        with open(action_path, 'rb') as f:
            all_data = pk.load(f)
        
        human_related_data = [x[0] for x in all_data]
        
        single_hpose_np = np.stack(human_related_data, axis=0)
        
        return single_hpose_np
    
    def split_single_pose(self, single_pose_array):
        T, _, _ = single_pose_array.shape
        
        iterations = np.ceil((T-self.win_size)/self.win_stride).astype(int)+1
        all_windows = []
        for segment in range(iterations):
            start_index = self.win_stride * segment
            end_index = start_index + self.win_size
            
            curr_win = single_pose_array[start_index:end_index]
            all_windows.append(curr_win)
        
        return np.stack(all_windows, axis=0)