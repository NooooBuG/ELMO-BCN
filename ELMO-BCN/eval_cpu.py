# This file makes use of the InferSent, SentEval and CoVe libraries, and may contain adapted code from the repositories
# containing these libraries. Their licenses can be found in <this-repository>/Licenses.
#
# CoVe:
#   Copyright (c) 2017, Salesforce.com, Inc. All rights reserved.
#   Repository: https://github.com/salesforce/cove
#   Reference: McCann, Bryan, Bradbury, James, Xiong, Caiming, and Socher, Richard. Learned in translation:
#              Contextualized word vectors. In Advances in Neural Information Processing Systems 30, pp, 6297-6308.
#              Curran Associates, Inc., 2017.
#

import sys
import os
import argparse
import timeit
import gc
from model_cpu import ELMOBCN

start_time = timeit.default_timer()

parser = argparse.ArgumentParser(description='Replication of the CoVe BCN using ELMO as input embedding')

parser.add_argument("--datadir", type=str, default='../datasets', help="Path to the directory that contains the datasets")
# parser.add_argument("--datadir", type=str, default='/cache/datasets', help="MedelArts:Path to the directory that contains the datasets")
# parser.add_argument("--outputdir", type=str, default='model', help="Path to the directory where the BCN model will be saved")
parser.add_argument("--outputdir", type=str, default='/cache/result', help="MedelArts:Path to the directory where the BCN model will be saved")

parser.add_argument("--mode", type=int, default=0, help="0: Normal (train + test); 1: BCN model dry-run (just try creating the model and do nothing else); 2: Train + test dry-run (Load a smaller dataset and train + test on it)")

parser.add_argument("--transfer_task", type=str, default="SSTFine", help="Transfer task used for training BCN and evaluating predictions (e.g. SSTBinary, SSTFine, SSTBinary_lower, SSTFine_lower, TREC6, TREC50, TREC6_lower, TREC50_lower)")

parser.add_argument("--n_epochs", type=int, default=20, help="Number of epochs (int). After 5 epochs of worse dev accuracy, training will early stopped and the best epoch will be saved (based on dev accuracy).")
parser.add_argument("--batch_size", type=int, default=8, help="Batch size (int)")
parser.add_argument("--same_bilstm_for_encoder", type=str, default="False", help="Whether or not to use the same BiLSTM (when flag is set) or separate BiLSTMs (flag unset) for the encoder (str: True or False)")
parser.add_argument("--bilstm_encoder_n_hidden", type=int, default=300, help="Number of hidden states in encoder's BiLSTM(s) (int)")
parser.add_argument("--bilstm_encoder_forget_bias", type=float, default=1.0, help="Forget bias for encoder's BiLSTM(s) (float)")
parser.add_argument("--bilstm_integrate_n_hidden", type=int, default=300, help="Number of hidden states in integrate's BiLSTMs (int)")
parser.add_argument("--bilstm_integrate_forget_bias", type=float, default=1.0, help="Forget bias for integrate's BiLSTMs (float)")
parser.add_argument("--dropout_ratio", type=float, default=0.1, help="Ratio for dropout applied before Feedforward Network and before each Batch Norm (float)")
parser.add_argument("--output_reduction", type=int, default=2, help="On the first and second maxout layers, the dimensionality is divided by this number (int)")
parser.add_argument("--optimizer", type=str, default="adam", help="Optimizer (adam or gradientdescent)")
parser.add_argument("--learning_rate", type=float, default=0.0001, help="Leaning rate (float)")
parser.add_argument("--adam_beta1", type=float, default=0.9, help="Beta1 for adam optimiser if adam optimiser is used (float)")
parser.add_argument("--adam_beta2", type=float, default=0.999, help="Beta2 for adam optimiser if adam optimiser is used (float)")
parser.add_argument("--adam_epsilon", type=float, default=1e-8, help="Epsilon for adam optimiser if adam optimiser is used (float)")

args, _ = parser.parse_known_args()

def str2bool(v):
  return v.lower() in ("yes", "true", "t", "1")

import sst_data



"""
HYPERPARAMETERS
"""

hyperparameters = {
    'n_epochs': args.n_epochs, # int
    'batch_size': args.batch_size, # int

    'same_bilstm_for_encoder': str2bool(args.same_bilstm_for_encoder), # boolean
    'bilstm_encoder_n_hidden': args.bilstm_encoder_n_hidden, # int. Used by McCann et al.: 300
    'bilstm_encoder_forget_bias': args.bilstm_encoder_forget_bias, # float

    'bilstm_integrate_n_hidden': args.bilstm_integrate_n_hidden, # int. Used by McCann et al.: 300
    'bilstm_integrate_forget_bias': args.bilstm_integrate_forget_bias, # float

    'dropout_ratio': args.dropout_ratio, # float. Used by McCann et al.: 0.1, 0.2 or 0.3
    'output_reduction': args.output_reduction, # int. Used by McCann et al.: 2, 4 or 8

    'optimizer': args.optimizer, # "adam" or "gradientdescent". Used by McCann et al.: "adam"
    'learning_rate': args.learning_rate, # float. Used by McCann et al.: 0.001
    'adam_beta1': args.adam_beta1, # float (used only if optimizer == "adam")
    'adam_beta2': args.adam_beta2, # float (used only if optimizer == "adam")
    'adam_epsilon': args.adam_epsilon # float (used only if optimizer == "adam")
}

if args.mode == 1:
    ELMOBCN(hyperparameters, 3, 128, 900, args.outputdir).dry_run()
    sys.exit()

if not os.path.exists(args.outputdir):
    os.makedirs(args.outputdir)

if not os.path.exists(os.path.join(args.outputdir, "info.txt")):
    with open(os.path.join(args.outputdir, "info.txt"), "w") as outputfile:
        outputfile.write(str(args.transfer_task) + "\n")
        outputfile.write(str(hyperparameters))

"""
DATASET
"""
if args.transfer_task == "SSTFine":
    dataset = sst_data.SSTFineDataset(args.datadir, dry_run=(args.mode == 2))
elif args.transfer_task == "SSTFine_lower":
    dataset = sst_data.SSTFineLowerDataset(args.datadir, dry_run=(args.mode == 2))
else:
    print("ERROR: Unknown transfer task. Set it correctly using the --transfer_task argument.")
    sys.exit(1)
gc.collect()

"""
BCN MODEL
"""

bcn = ELMOBCN(hyperparameters, dataset.get_n_classes(), dataset.get_max_sent_len(), args.outputdir)
dev_accuracy = bcn.train(dataset)
test_accuracy = bcn.test(dataset)

accuracy = {'dev': dev_accuracy, 'test': test_accuracy}
with open(os.path.join(args.outputdir, "accuracy.txt"), "w") as outputfile:
    outputfile.write(str(accuracy))

print("\nReal time taken to train + test: %s seconds" % (timeit.default_timer() - start_time))
