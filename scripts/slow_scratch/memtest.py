import sys, torch, resource
from transformers import AutoModelForCausalLM
torch.set_num_threads(2)
mode = sys.argv[1]
if mode == "a":
    m = AutoModelForCausalLM.from_pretrained("EleutherAI/pythia-1b", torch_dtype=torch.float32).eval()
else:
    m = AutoModelForCausalLM.from_pretrained("EleutherAI/pythia-1b", torch_dtype=torch.float16).eval()
    print("fp16 loaded", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6, flush=True)
    m = m.float()
print(mode, next(m.parameters()).dtype, "peak GB", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6, flush=True)
with torch.no_grad():
    m(torch.zeros((1, 1300), dtype=torch.long))
print("after forward peak GB", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6)
