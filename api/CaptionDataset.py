from nltk import tokenize
import pandas as pd
import torch
from torchvision import transforms
from torch.utils.data import Dataset
from os import listdir
from os.path import join
import spacy
from torch.nn.utils.rnn import pad_sequence
import cv2
import pickle



IMAGE_DIM = (256, 256)

spacy_eng = spacy.load("en_core_web_sm")
class Vocabulary:
    def __init__(self, freq_thres):
        self.itos = {0: "<PAD>", 1:"<SOS>", 2:"<EOS>", 3 :"<UNK>"}
        self.stoi = {"<PAD>": 0, "<SOS>": 1, "<EOS>": 2, "<UNK>": 3}
        self.freq_thres = freq_thres
    
    def __len__(self):
        return len(self.stoi)
    
    @staticmethod
    def tokenizer_eng(text):
        return [tok.text.lower() for tok in spacy_eng.tokenizer(text)]
    
    def build_vocabulary(self, captions):
        freq = {}
        idx = 4
        for sentence in captions:
            for word in self.tokenizer_eng(sentence):
                if word not in freq:
                    freq[word] = 1
                else:
                    freq[word] += 1
                
                if freq[word] == self.freq_thres:
                    self.stoi[word] = idx
                    self.itos[idx] = word
                    idx += 1
    
    def numericalize(self, text):
        tokened = self.tokenizer_eng(text)
        return [
            self.stoi[token] if token in self.stoi else self.stoi["<UNK>"]
            for token in tokened
        ]
    
    def saveVocabList(self):
        itosFile = open("itos.pkl", "wb")
        pickle.dump(self.itos, itosFile)
        itosFile.close()

        stoiFile = open("stoi.pkl", "wb")
        pickle.dump(self.stoi, stoiFile)
        stoiFile.close()

    def loadVocabList(self, itosPath, stoiPath):
        itosFile = open(itosPath, "rb")
        self.itos = pickle.load(itosFile)
        itosFile.close()

        stoiFile = open(stoiPath, "rb")
        self.stoi = pickle.load(stoiFile)
        stoiFile.close()

class CaptionDataset(Dataset):

    def __init__(self, csv_file, freq_thres):
        super().__init__()
        self.images = []
        self.sentences = []
        self.get_data(csv_file)
        self.vocab = Vocabulary(freq_thres)
        self.vocab.build_vocabulary(self.sentences)

        #print(self.sentences)

    def getSetImg(self, idx):
        return (self.images[idx], self.sentences[idx])
    
    def __len__(self):
        return len(self.images)
    
    def __getitem__(self, index):
        caption = self.sentences[index]

        numerical_cap = [self.vocab.stoi["<SOS>"]]
        numerical_cap += self.vocab.numericalize(caption)
        numerical_cap.append(self.vocab.stoi["<EOS>"])
        return (self.images[index], torch.tensor(numerical_cap))
    
    def get_data(self, csv_file):
        data = pd.read_csv(csv_file)
        numObs = len(data["Photo Number"])
        possibleImages = [file for file in listdir("./images")]
        #print(possibleImages)
        for i in range(numObs):
            imageNum = str(data["Photo Number"][i])
            imagePath = "observation (" + imageNum + ").png"
            if imagePath not in possibleImages:
                continue
            imagePath = "images/" + imagePath
            image = cv2.imread(imagePath)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image = self.tranformImage(image)
            self.images.append(image)

            sentence = data["Observation"][i]
            self.sentences.append(sentence)

    
    def tranformImage(self, image):
        preprocess = transforms.Compose([
            transforms.ToTensor(),
            transforms.CenterCrop(256 * 5),
            transforms.Resize(IMAGE_DIM)
        ])
        image = preprocess(image)
        return image


class Collate:
    def __init__(self, pad_idx):
        self.pad_idx = pad_idx

    def __call__(self, batch):
        imgs = [item[0].unsqueeze(0) for item in batch]
        imgs = torch.cat(imgs, dim = 0)
        targets = [item[1] for item in batch]
        targets = pad_sequence(targets, batch_first=False, padding_value=self.pad_idx)
        return imgs, targets

