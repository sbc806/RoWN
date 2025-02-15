import torch
from torch.distributions import MultivariateNormal

from ..hwn import HWN


def rotation_matrix(x, y):
    dim = x.size(-1)
    x = x / (x.norm(dim=-1, keepdim=True) + 1e-9)
    y = y / (y.norm(dim=-1, keepdim=True) + 1e-9)

    x = x[..., None]
    y = y[..., None]
    I = torch.eye(dim, device=x.device)
    tmp = y.matmul(x.transpose(-1, -2)) - x.matmul(y.transpose(-1, -2))
    R = I + tmp + 1 / (1 + (y * x).sum([-1, -2], keepdim=True)) * tmp.matmul(tmp)
    return R


class Distribution(HWN):
    def __init__(self, mean, covar) -> None:
        target_axis = mean[..., 1:]
        base_axis = torch.zeros(
            target_axis.size(), 
            device=mean.device
        )
        base_axis[..., 0] = torch.where(
            target_axis[..., 0] >= 0, 1, -1
        )
        print("mean:", mean, mean.shape)
        print("target_axis:", target_axis, target_axis.shape)
        print("base_axis:", base_axis, base_axis.shape)
        print("covar before R:", covar, covar.shape)
        R = rotation_matrix(base_axis, target_axis)

        covar = (R * covar[..., None, :]).matmul(R.transpose(-1, -2))
        print("R:", R, R.shape)
        print("covar:", covar, covar.shape)
        base = MultivariateNormal(
            torch.zeros(
                target_axis.size(), 
                device=covar.device
            ),
            covar
        )
        print(target_axis.size())
        print(torch.zeros(target_axis.size()).shape)
        super().__init__(mean, base)

    def log_prob(self, z):
        print("z.shape:", z.shape)
        u = self.manifold.logmap(self.mean, z)
        v = self.manifold.transp(self.mean, self.origin, u)
        print("v.shape:", v.shape)
        log_prob_v = self.base.log_prob(v[:, :, 1:])

        r = self.manifold.norm(u)
        log_det = (self.latent_dim - 1) * (torch.sinh(r).log() - r.log())

        log_prob_z = log_prob_v - log_det
        return log_prob_z

