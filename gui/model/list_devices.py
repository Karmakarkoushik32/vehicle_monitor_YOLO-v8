import torch

def list_devices():
    num_gpus = torch.cuda.device_count()
    return ['cpu',*[f"cuda:{device_id}|{torch.cuda.get_device_name(device_id)}" for device_id in range(num_gpus)]]
