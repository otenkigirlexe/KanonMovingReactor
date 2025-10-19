Place the VOSK model here.
The directory structure should be as follows.

model
│  README
│
├─am
│      final.mdl
│
├─conf
│      mfcc.conf
│      model.conf
│
├─graph
│  │  disambig_tid.int
│  │  Gr.fst
│  │  HCLr.fst
│  │  phones.txt
│  │  words.txt
│  │
│  └─phones
│          word_boundary.int
│
└─ivector
        final.dubm
        final.ie
        final.mat
        global_cmvn.stats
        online_cmvn.conf
        splice.conf

VOSK can be downloaded from the following URL.

https://alphacephei.com/vosk/models
