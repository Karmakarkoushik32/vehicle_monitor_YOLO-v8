import torch

def list_devices():
    num_gpus = torch.cuda.device_count()
    return ['cpu',*[torch.cuda.get_device_name(i) for i in range(num_gpus)]]
