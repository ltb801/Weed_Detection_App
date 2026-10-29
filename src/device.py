'''Inference-device selection without importing PyTorch during app startup.'''


def _cuda_is_available():
    import torch

    return torch.cuda.is_available()


def resolve_device(preference='auto'):
    '''Return a valid Torch device string for the requested preference.'''
    if preference not in {'auto', 'cpu', 'cuda:0'}:
        raise ValueError(f'Unsupported device preference: {preference}')
    if preference == 'cpu':
        return 'cpu'

    cuda_available = _cuda_is_available()
    if preference == 'auto':
        return 'cuda:0' if cuda_available else 'cpu'
    if not cuda_available:
        raise ValueError('NVIDIA GPU was selected, but CUDA is not available to PyTorch.')
    return preference
