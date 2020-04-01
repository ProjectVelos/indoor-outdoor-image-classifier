import torch
from torch.autograd import Variable as V
import torchvision.models as models
from torchvision import transforms as trn
from torch.nn import functional as F
import os
import numpy as np
import cv2
from PIL import Image
import cnn_files.wideresnet as wideresnet
import random
import hashlib


class VelosImageClassifier():

    def __init__(self):

        # load the labels
        self.classes, self.labels_IO, self.labels_attribute, self.W_attribute = self.load_labels()

        # load the model
        self.features_blobs = []
        self.load_model()

        # load the transformer
        self.tf = self.returnTF()  # image transformer

        # get the softmax weight
        self.params = list(self.model.parameters())
        self.weight_softmax = self.params[-2].data.numpy()
        self.weight_softmax[self.weight_softmax < 0] = 0


    def classify_file(self,img_file,generate_cam=False):
        return self._classify(img_file,generate_cam)

    def classify_url(self,img_url,generate_cam=False):
        rnd = random.randint(0,100000)
        rnd_hash = hashlib.md5(str(rnd).encode('UTF')).hexdigest()
        img_file = "/tmp/" + rnd_hash + ".jpg"
        os.system('wget %s -q -O %s' % (img_url,img_file))
        results = self._classify(img_file,generate_cam)
        os.remove(img_file)
        return results

    def _classify(self,img_file,generate_cam=False):
        result = {}
        self.features_blobs = []
        # load the test image
        # img_url = ''
        # os.system('wget %s -q -O test.jpg' % img_url)
        img = Image.open(img_file)
        input_img = V(self.tf(img).unsqueeze(0))

        # forward pass
        logit = self.model.forward(input_img)
        h_x = F.softmax(logit, 1).data.squeeze()
        probs, idx = h_x.sort(0, True)
        probs = probs.numpy()
        idx = idx.numpy()



        # output the IO prediction
        io_image = np.mean(self.labels_IO[idx[:10]])  # vote for the indoor or outdoor
        if io_image < 0.5:
            result["location"] = "Indoors"
        else:
            result["location"] = "Outdoors"


        # output the prediction of scene category
        result['categories'] = []
        for i in range(0, 10):
            if probs[i] > .1:
                result['categories'].append({"category": self.classes[idx[i]], "probability":probs[i]})

        # output the scene attributes
        result['attributes'] = []
        responses_attribute = self.W_attribute.dot(self.features_blobs[1])
        idx_a = np.argsort(responses_attribute)
        #print('--SCENE ATTRIBUTES:')
        #print(', '.join([self.labels_attribute[idx_a[i]] for i in range(-1, -10, -1)]))
        for i in range(-1, -10, -1):
            result['attributes'].append(self.labels_attribute[idx_a[i]])

        if generate_cam:

            CAMs = self.returnCAM(self.features_blobs[0], self.weight_softmax, [idx[0]])

            # render the CAM and output
            img = cv2.imread(img_file)
            height, width, _ = img.shape
            heatmap = cv2.applyColorMap(cv2.resize(CAMs[0], (width, height)), cv2.COLORMAP_JET)
            result = heatmap * 0.4 + img * 0.5
            cam_file = img_file.strip(".jpg") + "_cam.jpg"
            cv2.imwrite(cam_file, result)

        return result

    def load_labels(self):
        # prepare all the labels
        file_name_category = 'cnn_files/categories_places365.txt'
        classes = list()
        with open(file_name_category) as class_file:
            for line in class_file:
                classes.append(line.strip().split(' ')[0][3:])
        classes = tuple(classes)

        # indoor and outdoor relevant
        file_name_IO = 'cnn_files/IO_places365.txt'

        with open(file_name_IO) as f:
            lines = f.readlines()
            labels_IO = []
            for line in lines:
                items = line.rstrip().split()
                labels_IO.append(int(items[-1]) -1) # 0 is indoor, 1 is outdoor
        labels_IO = np.array(labels_IO)

        # scene attribute relevant
        file_name_attribute = 'cnn_files/labels_sunattribute.txt'
        with open(file_name_attribute) as f:
            lines = f.readlines()
            labels_attribute = [item.rstrip() for item in lines]

        file_name_W = 'cnn_files/W_sceneattribute_wideresnet18.npy'
        W_attribute = np.load(file_name_W)

        return classes, labels_IO, labels_attribute, W_attribute


    def hook_feature(self,module, input, output):
        self.features_blobs.append(np.squeeze(output.data.cpu().numpy()))

    def returnCAM(self,feature_conv, weight_softmax, class_idx):
        # generate the class activation maps upsample to 256x256
        size_upsample = (256, 256)
        nc, h, w = feature_conv.shape
        output_cam = []
        for idx in class_idx:
            cam = weight_softmax[class_idx].dot(feature_conv.reshape((nc, h*w)))
            cam = cam.reshape(h, w)
            cam = cam - np.min(cam)
            cam_img = cam / np.max(cam)
            cam_img = np.uint8(255 * cam_img)
            output_cam.append(cv2.resize(cam_img, size_upsample))
        return output_cam

    def returnTF(self):
    # load the image transformer
        tf = trn.Compose([
            trn.Resize((224,224)),
            trn.ToTensor(),
            trn.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        return tf


    def load_model(self):
        # this model has a last conv feature map as 14x14

        model_file = 'cnn_files/wideresnet18_places365.pth.tar'

        self.model = wideresnet.resnet18(num_classes=365)
        checkpoint = torch.load(model_file, map_location=lambda storage, loc: storage)
        state_dict = {str.replace(k,'module.',''): v for k,v in checkpoint['state_dict'].items()}
        self.model.load_state_dict(state_dict)
        self.model.eval()

        # hook the featu/re extractor
        features_names = ['layer4','avgpool'] # this is the last conv layer of the resnet
        for name in features_names:
            self.model._modules.get(name).register_forward_hook(self.hook_feature)

        #return model

#from pprint import pprint

#vi = VelosImageClassifier()
#vi.classify('test.jpg', True)
#r = vi.classify_url('https://www.visitcalifornia.com/sites/default/files/styles/welcome_image/public/Pillars_Outdoor_OR_RD_50003619_1280x640.jpg')

#r = vi.classify_url('https://www.salomon.com/sites/default/files/styles/crop_image_large_standard_mobile/public/paragraphs/cta/2019-08/Hiking-mobile%20V2_0.jpg?itok=B1JI6Qi3')
#pprint(r)
#r = vi.classify_url('https://dl1.cbsistatic.com/i/r/2018/08/09/b6ca69f8-f123-408c-9b1f-ea3f9cf1fb17/resize/620xauto/8787947d1d00135d3f2ed512e56bee72/concert-crowd.jpg')
#pprint(r)