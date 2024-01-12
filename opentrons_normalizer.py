from opentrons import protocol_api
from csv import DictReader


metadata = {
    'apiLevel': '2.13',
    'protocolName': 'Sample Normalizer 2.0',
    'description': '''This protocol requires two csv files -- params_normalizer.csv contains parameters that are not
sample-specific, and a second (variably named) csv file that contains sample-specific parameters. The results of this
protocol is a Kingfisher deep well plate with wells containing equal volumes and total protein concentrations.  There
are a few options available:
1. It will optionally add enolase/TCEP solution to all the relevant wells prior to protein normalization.
2. It will optionally mix the lysate prior to aspiration.
3. It will optionally use one or two control samples not in the lysate plate, and add to the final plate (w/ appropriate dilution)
4. It will optionally pause and wait for the disulfide reduction (done off line) and then add IAM.
At that point the protocol is finished and the deep
well plate is removed and allowed to react at room temperature, beads added manually, and acetonitrile added manually
using a multi-channel pipette. The iodoacetamide and tcep/enolase will be in a 1.5 ml eppies on sample rack 1.''',
    'author': 'Slick'
}

def run(protocol: protocol_api.ProtocolContext):
    #parameter file name (including the path)
    param_csv_file = 'params_normalizer.csv'

    #param_csv_file = '/data/user_storage/params_normalizer.csv'

    def strip_dict(d):
        return {key: strip_dict(value)
        if isinstance(value, dict)
        else value.strip()
                for key, value in d.items()}

    def CheckParameters():
        '''CheckParameters checks various parameters and compares with the csv file to look for any mistakes.
        Args: none
        Returns:    diluent_h (real) is the height to start pipetting from the diluent tube'''

        valid_tube_positions = set(['A1', 'A2', 'A3', 'A4', 'A5', 'A6',
                                    'B1', 'B2', 'B3', 'B4', 'B5', 'B6',
                                    'C1', 'C2', 'C3', 'C4', 'C5', 'C6',
                                    'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'CNTL1', 'CNTL2'
                                    ])
        valid_plate_locations = set(['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10', 'A11', 'A12',
                                     'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11', 'B12',
                                     'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C11', 'C12',
                                     'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12',
                                     'E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7', 'E8', 'E9', 'E10', 'E11', 'E12',
                                     'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12',
                                     'G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9', 'G10', 'G11', 'G12',
                                     'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'H7', 'H8', 'H9', 'H10', 'H11', 'H12', 'CNTL1',
                                     'CNTL2'
                                     ])
        valid_csv_keys = ['sample name', 'aspirate tray', 'aspirate location', 'dispense location', 'sample volume',
                          'diluent volume']
        valid_tray_nums = set(['0', '1', '2', '3', '4'])

        # check the csv column headers for empty spaces
        csv_keys = datums[0].keys()
        if len(csv_keys) < len(valid_csv_keys):
            raise Exception('The number of columns in the csv file is less than the required number.')
        for valid_key in valid_csv_keys:
            if valid_key not in csv_keys:
                raise Exception("You are missing the csv file header '{0}'".format(valid_key))

        # change lower case to upper case for the aspirate and dispense locations
        for datum in datums:
            datum['aspirate location'] = datum['aspirate location'].upper()
            datum['dispense location'] = datum['dispense location'].upper()

        # remove extraneous zeroes from aspirate and dispense locations
        for datum in datums:
            if datum['aspirate location'][1] == '0':
                datum['aspirate location'] = datum['aspirate location'][0] + datum['aspirate location'][2:]
            if datum['dispense location'][1] == '0':
                datum['dispense location'] = datum['dispense location'][0] + datum['dispense location'][2:]

        # check that the dispense locations are valid
        dispense_locations = [d['dispense location'] for d in datums]
        for location in dispense_locations:
            if location not in valid_plate_locations:
                raise Exception('One or more of the BCA dispense locations is not valid')

        # check that the sample locations are valid
        aspirate_locations = [d['aspirate location'] for d in datums]
        if number_of_sample_racks == 0:  # for samples in a plate, use the valid positions for a plate
            for location in aspirate_locations:
                if location not in valid_plate_locations:
                    raise Exception('One or more sample locations is not valid.')
        else:
            for location in aspirate_locations:
                if location not in valid_tube_locations:
                    raise Exception('One or more sample locations is not valid.')

        # check that there are enough trays for the number of samples
        if int(number_of_sample_racks) >= 1 and int(number_of_sample_racks) <= 4:
            if len(set(aspirate_locations)) > number_of_sample_racks * 24:
                raise Exception('Insufficent sample racks for the number of samples in the csv file.')
        elif int(number_of_sample_racks) == 0:
            if len(set(aspirate_locations)) > 96:
                raise Exception('Insufficent sample plates for the number of samples in the csv file.')

        # check that the aspirate tray numbers as strings are correct
        tray_numbers = [d['aspirate tray'] for d in datums]
        for tray in tray_numbers:
            if tray not in valid_tray_nums:
                raise Exception('There is an invalid tray number: {0}'.format(tray))

        # check that number samples will fit on the deep well plate
        if len(datums) > 96:
            raise Exception('There are too many samples to fit in one deep well Kingfisher plate.')

        # check that there is enough tcep/enolase
        if add_tcep:
            if len(datums) * tcep_vol_perWell + 20 > tcep_vol:
                raise Exception('There is not enough tcep reagent available.  You need at least {0} ul'.
                                format(len(datums) * tcep_vol_perWell + 20))

        # check that there is enough iam
        if add_iam:
            if len(datums) * iam_vol_perWell + 20 > iam_vol:
                raise Exception('There is not enough iam reagent available.  You need at least {0} ul'.
                                format(len(datums) * iam_vol_perWell + 20))

        # check that there is enough diluent
        needed_diluent_volume = 100  # num ul of extra diluent
        for datum in datums:
            needed_diluent_volume += float(datum['diluent volume'])
        if needed_diluent_volume > diluent_vol:
            raise Exception('There is not enough diluent.  You need at least {0} ul'.format(needed_diluent_volume))

        # check that there is enough control 1
        if control_1:
            needed_cntl1_vol = 100  # min vol of cntl1 in uls
            for datum in datums:
                if datum['aspirate location'] == 'CNTL1':
                    needed_cntl1_vol += float(datum['sample volume'])
            if cntl1_vol < needed_cntl1_vol:
                raise Exception('There is not enough control 1 volume.')

        # check that there is enough control 2
        if control_2:
            needed_cntl2_vol = 100  # min vol of cntl1 in uls
            for datum in datums:
                if datum['aspirate location'] == 'CNTL2': needed_cntl2_vol += float(datum['sample volume'])
            if cntl2_vol < needed_cntl2_vol:
                raise Exception('There is not enough control 2 volume.')

        # determine the starting height for the diluent
        if diluent_tube_size == '2 ml':
            if diluent_vol > 500:
                diluent_h = 10 + (diluent_vol - 500) * 0.0160 - 5
            else:
                diluent_h = 1
        elif diluent_tube_size == '15 ml':
            if diluent_vol > 1500:
                diluent_h = 23 + (
                            diluent_vol - 1500) * 0.00635 - 5  # mm to 1.5 ml=23; 1/pi*r2=0.00635; 5 is mm below surface
            else:
                diluent_h = 1
        elif diluent_tube_size == '50 ml':
            if diluent_vol > 4000:
                diluent_h = 20 + (reagent_vol - 4000) * 0.00175 - 5
            else:
                diluent_h = 1
        else:
            raise Exception('The diluent must be in either a 2 ml eppie or 15/50 ml Falcon tube.')

        # determine the starting height for the tcep/enolase
        if add_tcep:
            if tcep_tube_size == '2 ml':
                if tcep_vol > 500:
                    tcep_h = 10 + (tcep_vol - 500) * 0.0160 - 5
                else:
                    tcep_h = 1
            elif tcep_tube_size == '15 ml':
                if tcep_vol > 1500:
                    tcep_h = 23 + (tcep_vol - 1500) * 0.00635 - 5
                else:
                    tcep_h = 1
            elif tcep_tube_size == '50 ml':
                if tcep_vol > 4000:
                    tcep_h = 20 + (tcep_vol - 4000) * 0.00175 - 5
                else:
                    tcep_h = 1
            else:
                raise Exception('The tcep/enolase must be in either a 2 ml eppie or 15/50 ml Falcon tube.')
        else:
            tcep_h = 1  # need some sort of value even if its not being used

        # determine the starting height for the diluent
        if add_iam:
            if iam_tube_size == '2 ml':
                if iam_vol > 500:
                    iam_h = 10 + (iam_vol - 500) * 0.0160 - 5
                else:
                    iam_h = 1
            elif iam_tube_size == '15 ml':
                if iam_vol > 1500:
                    iam_h = 23 + (iam_vol - 1500) * 0.00635 - 5
                else:
                    iam_h = 1
            elif iam_tube_size == '50 ml':
                if iam_vol > 4000:
                    iam_h = 20 + (iam_vol - 4000) * 0.00175 - 5
                else:
                    iam_h = 1
            else:
                raise Exception('The IAM must be in either a 2 ml eppie or 15/50 ml Falcon tube.')
        else:
            iam_h = 1

        # determine starting height of control 1
        if control_1:
            if cntl1_tube_size == '2 ml':
                if cntl1_vol > 500:
                    cntl1_h = 10 + (cntl1_vol - 500) * 0.0160 - 5
                else:
                    cntl1_h = 1
            elif cntl1_tube_size == '15 ml':
                if cntl1_vol > 1500:
                    cntl1_h = 23 + (cntl1_vol - 1500) * 0.00635 - 5
                else:
                    cntl1_h = 1
            elif cntl1_tube_size == '50 ml':
                if cntl1_vol > 4000:
                    cntl1_h = 20 + (cntl1_vol - 4000) * 0.00175 - 5
                else:
                    cntl1_h = 1
            else:
                raise Exception('Control 1 must be in either a 2 ml eppie or 15/50 ml Falcon tube.')
        else:
            cntl1_h = 1

        # determine starting height of control 2
        if control_2:
            if cntl2_tube_size == '2 ml':
                if cntl2_vol > 500:
                    cntl2_h = 10 + (cntl2_vol - 500) * 0.0160 - 5
                else:
                    cntl2_h = 1
            elif cntl2_tube_size == '15 ml':
                if cntl2_vol > 1500:
                    cntl2_h = 23 + (cntl2_vol - 1500) * 0.00635 - 5
                else:
                    cntl2_h = 1
            elif cntl2_tube_size == '50 ml':
                if cntl2_vol > 4000:
                    cntl2_h = 20 + (cntl2_vol - 4000) * 0.00175 - 5
                else:
                    cntl2_h = 1
            else:
                raise Exception('Control 2 must be in either a 2 ml eppie or 15/50 ml Falcon tube.')
        else:
            cntl2_h = 1

        return diluent_h, tcep_h, iam_h, cntl1_h, cntl2_h

    def ChangeHeightVolume(height, volume, load_vol, tube_size):
        '''ChangeDiluentHeight changes the diluent height after each addition of diluent
            Args:       height (real) is the height above the bottom of the tube to aspirate
                        volume (real) is the volume of the diluent in the diluent tube
                        load_vol (real) is the volume just aspirated that determines the change in height
                        tube_size (str) indicates whether the tube is 1.5 ml eppie, or 15/50 ml Falcon
            Returns:    height is as described above
                        volume is as described above'''
        volume = volume - load_vol
        if tube_size == '2 ml':
            if volume < 500:
                height = 1
            else:
                height -= (load_vol * 0.0160)
        elif tube_size == '15 ml':
            if volume < 1500:
                height = 1
            else:
                height -= (load_vol * 0.00635)
        elif tube_size == '50 ml':
            if volume < 4000:
                height = 1
            else:
                height -= (load_vol * 0.00175)

        if height < 1: height = 1
        return height, volume

    def StrToBool(val):
        '''Converts a string to Boolean'''
        val = val.lower()
        if val in ('y', 'yes', 't', 'true', 'on', '1', 'yup'):
            return True
        elif val in ('n', 'no', 'f', 'false', 'off', '0', 'nope'):
            return False
        else:
            raise ValueError("invalid truth value %r" % (val,))

    def GetAspirateLocation(datum):

        if datum['aspirate location'] == 'CNTL1':
            aspirate_location = cntl1_location
        elif datum['aspirate location'] == 'CNTL2':
            aspirate_location = cntl2_location
        elif datum['aspirate tray'] == '0':
            aspirate_location = sample_rack0[datum['aspirate location']]
        elif datum['aspirate tray'] == '1':
            aspirate_location = sample_rack1[datum['aspirate location']]
        elif datum['aspirate tray'] == '2':
            aspirate_location = sample_rack2[datum['aspirate location']]
        elif datum['aspirate tray'] == '3':
            aspirate_location = sample_rack3[datum['aspirate location']]
        elif datum['aspirate tray'] == '4':
            aspirate_location = sample_rack4[datum['aspirate location']]
        else:
            raise Exception('Something weird happened in GetAspirateLocation')

        return aspirate_location

    # ======================================================================================================================
    # ======================================================================================================================
    protocol.set_rail_lights(True)  # turn the lights on

    # read the parameter file
    with open(param_csv_file, 'r') as readerObj:
        dict_reader = DictReader(readerObj)
        parameters = list(dict_reader)
    for parameter in parameters:
        if parameter['variable'] == 'inputCSVfilename': inputCSVfilename = parameter['value'].rstrip().lstrip()
        if parameter['variable'] == 'number_of_sample_racks': number_of_sample_racks = int(
            parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'sample_aspiration_height': sample_aspiration_height = float(
            parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'aspiration_delay_sec': aspiration_delay_sec = float(
            parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'mix': mix = StrToBool(parameter['value'])
        if parameter['variable'] == 'mix_vol': mix_vol = float(parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'mix_reps': mix_reps = int(parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'diluent_location': diluent_location = parameter['value'].rstrip().lstrip()
        if parameter['variable'] == 'diluent_tube_size': diluent_tube_size = parameter['value'].rstrip().lstrip()
        if parameter['variable'] == 'diluent_vol': diluent_vol = float(parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'add_tcep': add_tcep = StrToBool(parameter['value'])
        if parameter['variable'] == 'tcep_location': tcep_location = parameter['value'].rstrip().lstrip()
        if parameter['variable'] == 'tcep_tube_size': tcep_tube_size = parameter['value'].rstrip().lstrip()
        if parameter['variable'] == 'tcep_vol': tcep_vol = float(parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'tcep_vol_perWell': tcep_vol_perWell = float(parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'add_iam': add_iam = StrToBool(parameter['value'])
        if parameter['variable'] == 'iam_location': iam_location = parameter['value'].rstrip().lstrip()
        if parameter['variable'] == 'iam_tube_size': iam_tube_size = parameter['value'].rstrip().lstrip()
        if parameter['variable'] == 'iam_vol': iam_vol = float(parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'iam_vol_perWell': iam_vol_perWell = float(parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'control_1': control_1 = StrToBool(parameter['value'])
        if parameter['variable'] == 'cntl1_location': cntl1_location = parameter['value'].rstrip().lstrip()
        if parameter['variable'] == 'cntl1_tube_size': cntl1_tube_size = parameter['value'].rstrip().lstrip()
        if parameter['variable'] == 'cntl1_vol': cntl1_vol = float(parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'control_2': control_2 = StrToBool(parameter['value'])
        if parameter['variable'] == 'cntl2_location': cntl2_location = parameter['value'].rstrip().lstrip()
        if parameter['variable'] == 'cntl2_tube_size': cntl2_tube_size = parameter['value'].rstrip().lstrip()
        if parameter['variable'] == 'cntl2_vol': cntl2_vol = float(parameter['value'].rstrip().lstrip())

    # labware
    p300_tip_rack1 = protocol.load_labware('opentrons_96_tiprack_300ul', '5', '300ul tiprack')
    p300_tip_rack2 = protocol.load_labware('opentrons_96_tiprack_300ul', '2', '300ul tiprack')
    p20_tip_rack1 = protocol.load_labware('opentrons_96_tiprack_20ul', '6', '20ul tiprack')
    p20_tip_rack2 = protocol.load_labware('opentrons_96_tiprack_20ul', '3', '20ul tiprack')
    plate = protocol.load_labware('thermoscientificnunc_96_wellplate_1300ul', '8', 'digest plate')
    # plate = protocol.load_labware('kingfisherdeepwell_96_wellplate_2300ul', '8', 'king fisher plate')
    tube_rack = protocol.load_labware('opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical', '9',
                                      '15 and 50 ml tube rack')
    twoMLtube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10',
                                           '2 ml tube rack')
    if number_of_sample_racks == 1:
        sample_rack1 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '11',
                                             'sample rack1')
    elif number_of_sample_racks == 2:
        sample_rack1 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '11',
                                             'sample rack1')
        sample_rack2 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '10',
                                             'sample rack2')
    elif number_of_sample_racks == 3:
        sample_rack1 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '11',
                                             'sample rack1')
        sample_rack2 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '10',
                                             'sample rack2')
        sample_rack3 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '7',
                                             'sample rack3')
    elif number_of_sample_racks == 4:
        sample_rack1 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '11',
                                             'sample rack1')
        sample_rack2 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '10',
                                             'sample rack2')
        sample_rack3 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '7',
                                             'sample rack3')
        sample_rack4 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '4',
                                             'sample rack4')
    elif number_of_sample_racks == 0:
        sample_rack0 = protocol.load_labware('thermoscientificnunc_96_wellplate_1300ul', '11', 'lysate plate')
        # sample_rack0 = protocol.load_labware('kingfisherdeepwell_96_wellplate_2300ul', '11', 'lysate plate')
    else:
        raise Exception('You are limited to no more than four sample racks, or a single 96 deep well plate.')

    # reagent locations
    if diluent_tube_size == '50 ml' or diluent_tube_size == '15 ml':
        diluent_location = tube_rack[diluent_location]
    elif diluent_tube_size == '2 ml':
        diluent_location = twoMLtube_rack[diluent_location]
    else:
        raise Exception('diluent_tube_size must be 50 ml, 15 ml, or 2 ml')
    if tcep_tube_size == '50 ml' or tcep_tube_size == '15 ml':
        tcep_location = tube_rack[tcep_location]
    elif tcep_tube_size == '2 ml':
        tcep_location = twoMLtube_rack[tcep_location]
    else:
        raise Exception('tcep_tube_size must be 50 ml, 15 ml, or 2 ml')
    if iam_tube_size == '50 ml' or iam_tube_size == '15 ml':
        iam_location = tube_rack[iam_location]
    elif iam_tube_size == '2 ml':
        iam_location = twoMLtube_rack[iam_location]
    else:
        raise Exception('iam_tube_size must be 50 ml, 15 ml, or 2 ml')
    if cntl1_tube_size == '50 ml' or cntl1_tube_size == '15 ml':
        cntl1_location = tube_rack[cntl1_location]
    elif cntl1_tube_size == '2 ml':
        cntl1_location = twoMLtube_rack[cntl1_location]
    else:
        raise Exception('cntl1_tube_size must be 50 ml, 15 ml, or 2 ml')
    if cntl2_tube_size == '50 ml' or cntl2_tube_size == '15 ml':
        cntl2_location = tube_rack[cntl2_location]
    elif cntl2_tube_size == '2 ml':
        cntl2_location = twoMLtube_rack[cntl2_location]
    else:
        raise Exception('cntl2_tube_size must be 50 ml, 15 ml, or 2 ml')

    # pipettes
    p300 = protocol.load_instrument("p300_single_gen2", mount="left", tip_racks=[p300_tip_rack1, p300_tip_rack2])
    p20 = protocol.load_instrument("p20_single_gen2", mount="right", tip_racks=[p20_tip_rack1, p20_tip_rack2])

    # read the sample csv
    with open(inputCSVfilename, 'r') as readerObj:
        dict_reader = DictReader(readerObj)
        rows = list(dict_reader)
    datums = []
    for datum in rows:  # strip white space from strings in the list of dicts
        datum = strip_dict(datum)
        datums.append(datum)

    # check parameters and calculate the diluent height, change in height per well loading, and diluent height
    diluent_h, tcep_h, iam_h, cntl1_h, cntl2_h = CheckParameters()

    # add the tcep/enolase to the relevant sample wells in the Kingfisher deep well plate
    if add_tcep:
        p300.well_bottom_clearance.aspirate = 1  # make sure it goes to the bottom
        p20.well_bottom_clearance.aspirate = 1  # make sure it goes to the bottom
        dispense_locations = [d['dispense location'] for d in datums]
        if tcep_vol_perWell > 20:
            p300.pick_up_tip()
            for well in dispense_locations:
                p300.well_bottom_clearance.aspirate = tcep_h
                p300.aspirate(tcep_vol_perWell, tcep_location)
                p300.touch_tip(radius=0.9, v_offset=-2)
                p300.dispense(tcep_vol_perWell, plate[well])
                p300.touch_tip(radius=0.9, v_offset=-2)
                tcep_h, tcep_vol = ChangeHeightVolume(tcep_h, tcep_vol, tcep_vol_perWell, tcep_tube_size)
            p300.drop_tip()
        else:
            p20.pick_up_tip()
            for well in dispense_locations:
                p20.well_bottom_clearance.aspirate = tcep_h
                p20.aspirate(tcep_vol_perWell, tcep_location)
                p20.touch_tip(radius=0.9, v_offset=-2)
                p20.dispense(tcep_vol_perWell, plate[well])
                p20.touch_tip(radius=0.9, v_offset=-2)
                tcep_h, tcep_vol = ChangeHeightVolume(tcep_h, tcep_vol, tcep_vol_perWell, tcep_tube_size)
            p20.drop_tip()

    # dilute the samples into the Kingfisher deep well plate
    for i in range(len(datums)):
        p300.well_bottom_clearance.aspirate = sample_aspiration_height
        p20.well_bottom_clearance.aspirate = sample_aspiration_height
        sample_load_vol = float(datums[i]['sample volume'])
        diluent_load_vol = float(datums[i]['diluent volume'])
        aspirate_location = GetAspirateLocation(datums[i])
        if sample_load_vol > 20:
            p300.pick_up_tip()
            if mix: p300.mix(mix_reps, mix_vol, aspirate_location)
            p300.aspirate(sample_load_vol, aspirate_location)
            protocol.delay(seconds=aspiration_delay_sec)
            p300.touch_tip(radius=0.9, v_offset=-2)
            p300.dispense(sample_load_vol, plate[datums[i]['dispense location']])
            p300.touch_tip(radius=0.9, v_offset=-2)
            p300.drop_tip()
        elif sample_load_vol > 0:
            if mix:
                p300.pick_up_tip()
                p300.mix(mix_reps, mix_vol, aspirate_location)
                p300.drop_tip()
            p20.pick_up_tip()
            p20.aspirate(sample_load_vol, aspirate_location)
            protocol.delay(seconds=aspiration_delay_sec)
            p20.touch_tip(radius=0.9, v_offset=-2)
            p20.dispense(sample_load_vol, plate[datums[i]['dispense location']])
            p20.touch_tip(radius=0.9, v_offset=-2)
            p20.drop_tip()

        # load the diluent, if there is any
        if diluent_load_vol > 20:
            p300.well_bottom_clearance.aspirate = diluent_h
            p300.pick_up_tip()
            p300.aspirate(diluent_load_vol, diluent_location)
            p300.touch_tip(radius=0.9, v_offset=-2)
            p300.dispense(diluent_load_vol, plate[datums[i]['dispense location']])
            p300.touch_tip(radius=0.9, v_offset=-2)
            p300.drop_tip()
            diluent_h, diluent_vol = ChangeHeightVolume(diluent_h, diluent_vol, diluent_load_vol, diluent_tube_size)
        elif diluent_load_vol > 0:
            p20.well_bottom_clearance.aspirate = diluent_h
            p20.pick_up_tip()
            p20.aspirate(diluent_load_vol, diluent_location)
            p20.touch_tip(radius=0.9, v_offset=-2)
            p20.dispense(diluent_load_vol, plate[datums[i]['dispense location']])
            p20.touch_tip(radius=0.9, v_offset=-2)
            p20.drop_tip()
            diluent_h, diluent_vol = ChangeHeightVolume(diluent_h, diluent_vol, diluent_load_vol, diluent_tube_size)

    # pause while the plate is heated for disulfide reduction using the added tcep, and then cooled to rt
    if add_iam:
        protocol.home()
        protocol.pause('Place the deep well plate in a thermomixer for disulfide reduction, cool to room temperature,'
                       'and then return the deep well plate to slot 3.  The samples can now be frozen for storage.')

        # add iodoacetamide to the relevant sample wells in the Kingfisher deep well plate
        p300.well_bottom_clearance.aspirate = 1  # make sure it goes to the bottom
        p20.well_bottom_clearance.aspirate = 1  # make sure it goes to the bottom
        dispense_locations = [d['dispense location'] for d in datums]
        if iam_vol_perWell > 20:
            for well in dispense_locations:
                p300.well_bottom_clearance.aspirate = iam_h
                p300.pick_up_tip()
                p300.aspirate(iam_vol_perWell, iam_location)
                p300.touch_tip(radius=0.9, v_offset=-2)
                p300.dispense(iam_vol_perWell, plate[well])
                p300.touch_tip(radius=0.9, v_offset=-2)
                p300.drop_tip()
                iam_h, iam_vol = ChangeHeightVolume(iam_h, iam_vol, iam_vol_perWell, iam_tube_size)
        else:
            for well in dispense_locations:
                p20.well_bottom_clearance.aspirate = iam_h
                p20.pick_up_tip()
                p20.aspirate(iam_vol_perWell, iam_location)
                p20.touch_tip(radius=0.9, v_offset=-2)
                p20.dispense(iam_vol_perWell, plate[well])
                p20.touch_tip(radius=0.9, v_offset=-2)
                p20.drop_tip()
                iam_h, iam_vol = ChangeHeightVolume(iam_h, iam_vol, iam_vol_perWell, iam_tube_size)

    protocol.set_rail_lights(False)  # turn the lights off