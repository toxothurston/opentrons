# Opentrons OT2 Protocols
Python script protocols:
1. opentrons_normalizer.py: given samples in 1.5 ml eppies or in a single deep well plate, this script will produce a deep well plate containing the same volume and same protein quantity
2. bca_assay.py: given samples in 1.5 ml eppies or in a single deep well plate, this script produces a plate suitable for a BCA assay

Each script has a params csv file and a samples specific csv file, and examples for each script are provided.  The parameter file examples are bca_assay_params.csv and params_normalize.csv.  The BCA sample-specific csv file example is bsa_with_dilutions.csv, and the normalizer sample-specific csv file is PracticeSet1t2.csv.  All of these csv files have to be located in a particular Linux directory on board the OT2 at /data/user_storage/.  For both python scripts, you might have to edit the path (near the beginning of the Python file) for the params file, as they are hard coded into the .py file.  Note that after changing to the Linux path, and then importing it as a protocol that the OT2 app will complain that it cannot find the params file.  This is because it is looking in the desktop PC directories, and not the Linux directories of the on board computer.  It still will run, though.  Here are some hand and relevant Linux tips:

Connect to OT2: 
>>ssh -i ot2_ssh_key root@IP_ADRESS

Transfer a file from PC to OT2 (from the PC's C drive after opening powershell): 
>>scp -i ot2_ssh_key /path/on/computer root@IP_ADDRESS:/data/user_storage/AND_ANY_SUBFOLDERS
nb: the path on the PC can include the drive letter, eg, H:\csvFile
