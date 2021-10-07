# -*- coding:UTF-8 -*-
"""
predict
@Cai Yichao 2020_09_23
"""

import torch
import torchvision.transforms as transforms
#import torch.backends.cudnn as cudnn
from models.vgg import *
from PIL import Image
import time
import argparse
from utils.arg_utils import *

parser = argparse.ArgumentParser()
parser.add_argument('--file', '-f', type=str)
parse_args = parser.parse_args()

args = fetch_args()
#classes = ['s1', 's2', 's3', 's4', 's8', 's9', 's10', 's11', 's12', 's13', 's14',
#          's15', 's16', 's17', 's18', 's19', 's20', 's21', 's22', 's23', 's24',
#         's25', 's26', 's27', 's28', 's29', 's30', 's31', 's32', 's33', 's34', 
#         's35', 's36', 's37', 's38', 's39', 's40']

# 读取分类
classes = []
with open(args['class_file'], 'r') as f:
    for line in f:
        classes.append(line.strip())
num_classes = len(classes)


device = 'cuda' if torch.cuda.is_available() else 'cpu'

transform = transforms.Compose([transforms.Resize(args['input_size']),
                                transforms.ToTensor(),
                                transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))])
"""
loading model
"""
# create model
model = VGG_19(num_classes=num_classes).to(device)
# load model weights
model_weight_path = args['ckpt_path']+'/ckpt_1_acc0.00.pt'
model.load_state_dict(torch.load(model_weight_path, map_location=device)['net'])
model.eval()

"""
loading image
"""
img = Image.open("C:/Users/ASUS/Desktop/lfw/Zulfiqar_Ahmed/Zulfiqar_Ahmed_0001.jpg")
# [N, C, H, W]
img = transform(img)
# expand batch dimension
img = torch.unsqueeze(img, dim=0)
with torch.no_grad():
    # predict class
    output = torch.squeeze(model(img.to(device))).cpu()
    predict = torch.softmax(output, dim=0)
    predict_cla = torch.argmax(predict).numpy()

print_res = "class: {} prob: {:.3}".format(classes[predict_cla], predict[predict_cla].numpy())
print(print_res)



#ckpt_file = args['ckpt_path']+'/ckpt_1_acc0.00.pt'
#net = VGG_19(num_classes=num_classes)
#ckpt = torch.load(ckpt_file)
## if device is 'cuda':
##     net = torch.nn.DataParallel(net)
##     cudnn.benchmark = True

#net.to(device)
#net.load_state_dict(ckpt['net'])
#net.eval()

#start_time = time.time()
##image = Image.open(parse_args.file)
#image = Image.open("C:/Users/ASUS/Desktop/lfw/Zulfiqar_Ahmed/Zulfiqar_Ahmed_0001.jpg")
#image = transform(image)
#image = image.unsqueeze(0)
#image = image.to(device)

#with torch.no_grad():
#    out = net(image)
#    _, predict = out.max(1)
#    predict_cla = torch.argmax(predict).numpy()
#    print(predict[predict_cla].numpy())
#    print(classes[predict[0]])
#print("cost time: %.2f"%(time.time()-start_time))
