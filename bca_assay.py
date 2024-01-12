from opentrons import protocol_api
from csv import DictReader


metadata = {
    'apiLevel': '2.13',
    'protocolName': 'BCA assay v2.0',
    'description': '''This protocol creates a BCA assay plate from up to 72 samples and calibrants.  A csv file is needed that specifies
the 'sample name', 'aspirate tray', 'aspirate location', and the 'dilution' of the sample.The BCA reagent is dispensed 
to the 'aspirate locations', using a volume in ul specified by the variable 'reagent_vol_perWell'.  The BCA reagent
can be located in a 15 ml or 50 ml Falcon tube (specified using the variable 'reagent_tube_size'.''',
    'author': 'Slick'
}

def run(protocol: protocol_api.ProtocolContext):
    # Here's the params file (it must be called bca_assay_params.csv)
    param_csv_file = 'bca_assay_params.csv'

    # param_csv_file = '/data/user_storage/csv/bca_assay_params.csv'

    def ChangeReagentHeightVolume(reagent_h, reagent_vol):
        '''ChangeReagentHeight changes the BCA reagent height after each addition of reagent
                Args:       reagent_h (real) is the height above the bottom of the tube to aspirate
                            reagent_vol (real) is the volume of the reagent in the reagent tube
                Returns:    reagent_h is as described above
                            reagent_vol is as described above'''
        reagent_vol = reagent_vol - reagent_vol_perWell
        reagent_h -= reagent_delta_h
        if reagent_vol < reagent_vol_perWell: raise Exception('Insufficient BCA reagent volume.')
        if reagent_h < 1: reagent_h = 1
        return reagent_h, reagent_vol

    def ChangeDiluentHeightVolume(diluent_h, diluent_vol, diluent_load_vol):
        '''ChangeDiluentHeight changes the diluent height after each addition of diluent
            Args:       diluent_h (real) is the height above the bottom of the tube to aspirate
                        diluent_vol (real) is the volume of the diluent in the diluent tube
                        diluent_load_vol (real) is the volume just aspirated that determines the change in height
            Returns:    diluent_h is as described above
                        diluent_vol is as described above'''
        diluent_vol = diluent_vol - diluent_load_vol
        if diluent_tube_size == '15 ml': diluent_delta_h = diluent_load_vol * 0.00635
        if diluent_tube_size == '50 ml': diluent_delta_h = diluent_load_vol * 0.00175
        if diluent_vol < sample_vol_perWell: raise Exception('Insufficient diluent volume.')
        diluent_h -= diluent_delta_h
        if diluent_h < 1: diluent_h = 1
        return diluent_h, diluent_vol

    def CheckParameters():
        '''CheckParameters checks various parameters and compares with the csv file to look for any mistakes.
        Args: none
        Returns:    reagent_h (real) is the height to start pipetting from the BCA reagent tube
                    reagent_delta_h (real) is the drop in height after each pipetting of BCA reagent from one well'''

        valid_tube_locations = set(['A1', 'A2', 'A3', 'A4', 'A5', 'A6',
                                    'B1', 'B2', 'B3', 'B4', 'B5', 'B6',
                                    'C1', 'C2', 'C3', 'C4', 'C5', 'C6',
                                    'D1', 'D2', 'D3', 'D4', 'D5', 'D6'
                                    ])
        valid_plate_locations = set(['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10', 'A11', 'A12',
                                     'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11', 'B12',
                                     'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C11', 'C12',
                                     'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12',
                                     'E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7', 'E8', 'E9', 'E10', 'E11', 'E12',
                                     'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12',
                                     'G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9', 'G10', 'G11', 'G12',
                                     'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'H7', 'H8', 'H9', 'H10', 'H11', 'H12'
                                     ])
        valid_csv_keys = ['sample name', 'aspirate tray', 'aspirate location', 'dilution', 'dispense location']
        valid_tray_numbers = ['0', '1', '2', '3', '4']

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

        # check if number_of_sample_racks is zero, and if so, change the aspirate tray to zero
        if number_of_sample_racks == 0:
            for datum in datums:
                datum['aspirate tray'] = '0'

        # check that the aspirate tray numbers as strings are correct
        tray_numbers = [d['aspirate tray'] for d in datums]
        for tray_number in tray_numbers:
            if tray_number not in valid_tray_numbers:
                raise Exception('One or more of the tray numbers is not valid')

        # check that there are enough trays for the number of samples
        if int(number_of_sample_racks) >= 1 and int(number_of_sample_racks) <= 4:
            if len(set(aspirate_locations)) > number_of_sample_racks * 24:
                raise Exception('Insufficent sample racks for the number of samples in the csv file.')
        elif int(number_of_sample_racks) == 0:
            if len(set(aspirate_locations)) > 96:
                raise Exception('Insufficent sample plates for the number of samples in the csv file.')

        # check that number samples and dilutions will fit on the BCA plate
        if len(datums) > 96:
            raise Exception('There are too many samples and dilutions to fit on this 96 well BCA plate.')

        # check that there is a dilutent if there are any dilutions
        dilutions = [d['dilution'] for d in datums]
        for dilution in dilutions:
            if float(dilution) > 1 and diluent_location == '':
                raise Exception('The csv file says there are sample dilutions, but no diluent position specified.')

        # check that the dilution is reasonable
        for dilution in dilutions:
            if float(dilution) < 1 or float(dilution) > 25:
                raise Exception('The dilution can be a minimum of 1 and maximum of 25.')

        # check that there is enough BCA reagent for all the samples
        if aspirate_reagent:
            if len(datums) * reagent_vol_perWell > reagent_vol: raise Exception('Insufficient BCA reagent volume, '
                                                                                'given the number of samples.')

        # determine the starting height for the reagent and the change in height per well
        if reagent_tube_size == '15 ml':
            if reagent_vol > 1500:
                reagent_h = 23 + (reagent_vol - 1500) * 0.00635 - 5
                reagent_delta_h = reagent_vol_perWell * 0.00635
            else:
                reagent_h = 1
                reagent_delta_h = 0
        elif reagent_tube_size == '50 ml':
            if reagent_vol > 4000:
                reagent_h = 20 + (reagent_vol - 4000) * 0.00175 - 5
                reagent_delta_h = reagent_vol_perWell * 0.00175
            else:
                reagent_h = 1
                reagent_delta_h = 0
        else:
            raise Exception('The BCA reagent must be in either a 15 ml or 50 ml Falcon tube.')

        # determine the starting height for the diluent
        if diluent_tube_size == '15 ml':
            if diluent_vol > 1500:
                diluent_h = 23 + (diluent_vol - 1500) * 0.00635 - 5
            else:
                diluent_h = 1
        elif diluent_tube_size == '50 ml':
            if diluent_vol > 4000:
                diluent_h = 20 + (reagent_vol - 4000) * 0.00175 - 5
            else:
                diluent_h = 1
        else:
            raise Exception('The diluent must be in either a 15 ml or 50 ml Falcon tube.')

        return reagent_h, reagent_delta_h, diluent_h

    def strip_dict(d):
        return {key: strip_dict(value)
        if isinstance(value, dict)
        else value.strip()
                for key, value in d.items()}

    def GetAspirateLocation(datum):

        if datum['aspirate tray'] == '0':
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

    def StrToBool(val):
        '''Converts a string to Boolean'''
        val = val.lower()
        if val in ('y', 'yes', 't', 'true', 'on', '1', 'yup'):
            return True
        elif val in ('n', 'no', 'f', 'false', 'off', '0', 'nope'):
            return False
        else:
            raise ValueError("invalid truth value %r" % (val,))

    # ==================================================================================================================
    # ==================================================================================================================
    protocol.set_rail_lights(True)  # turn the lights on

    # read the parameter csv file
    with open(param_csv_file, 'r', encoding='utf-8-sig') as readerObj:
        dict_reader = DictReader(readerObj)
        parameters = list(dict_reader)
    for parameter in parameters:
        if parameter['variable'] == 'inputCSVfilename': inputCSVfilename = parameter['value'].rstrip().lstrip()
        if parameter['variable'] == 'number_of_sample_racks': number_of_sample_racks = int(
            parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'sample_vol_perWell': sample_vol_perWell = float(
            parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'sample_aspiration_height': sample_aspiration_height = float(
            parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'aspiration_delay_sec': aspiration_delay_sec = float(
            parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'mix': mix = StrToBool(parameter['value'])
        if parameter['variable'] == 'mix_reps': mix_reps = int(parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'mix_vol': mix_vol = float(parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'aspirate_reagent': aspirate_reagent = StrToBool(parameter['value'])
        if parameter['variable'] == 'reagent_vol_perWell': reagent_vol_perWell = float(
            parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'reagent_vol': reagent_vol = float(parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'reagent_tube_size': reagent_tube_size = parameter['value'].rstrip().lstrip()
        if parameter['variable'] == 'reagent_location': reagent_location = parameter['value'].rstrip().lstrip()
        if parameter['variable'] == 'diluent_vol': diluent_vol = float(parameter['value'].rstrip().lstrip())
        if parameter['variable'] == 'diluent_tube_size': diluent_tube_size = parameter['value'].rstrip().lstrip()
        if parameter['variable'] == 'diluent_location': diluent_location = parameter['value'].rstrip().lstrip()

    # labware
    p300_tip_rack1 = protocol.load_labware('opentrons_96_tiprack_300ul', '5', '300ul tiprack')
    p300_tip_rack2 = protocol.load_labware('opentrons_96_tiprack_300ul', '2', '300ul tiprack')
    p20_tip_rack1 = protocol.load_labware('opentrons_96_tiprack_20ul', '6', '20ul tiprack')
    p20_tip_rack2 = protocol.load_labware('opentrons_96_tiprack_20ul', '3', '20ul tiprack')
    plate = protocol.load_labware('armadillo_96_wellplate_200ul_pcr_full_skirt', '8', 'bca plate')
    # plate = protocol.load_labware('thermofisherscientific_96_wellplate_400ul', '8', 'bca plate')
    reagent_tubes = protocol.load_labware('opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical', '4', 'reagents')
    if number_of_sample_racks == 1:
        sample_rack1 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '11',
                                             'sample tube rack 1')
    elif number_of_sample_racks == 2:
        sample_rack1 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '11',
                                             'sample tube rack 1')
        sample_rack2 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '10',
                                             'sample tube rack 2')
    elif number_of_sample_racks == 3:
        sample_rack1 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '11',
                                             'sample tube rack 1')
        sample_rack2 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '10',
                                             'sample tube rack 2')
        sample_rack3 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '7',
                                             'sample tube rack 3')
    elif number_of_sample_racks == 4:
        sample_rack1 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '11',
                                             'sample tube rack 1')
        sample_rack2 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '10',
                                             'sample tube rack 2')
        sample_rack3 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '7',
                                             'sample tube rack 3')
        sample_rack4 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '9',
                                             'sample tube rack 4')
    elif number_of_sample_racks == 0:
        sample_rack0 = protocol.load_labware('thermoscientificnunc_96_wellplate_1300ul', '11', 'lysate plate')
        # sample_rack4 = protocol.load_labware('kingfisherdeepwell_96_wellplate_2300ul', '11', 'lysate plate')
    else:
        raise Exception('You are limited to no more than four sample racks, or use 0 for a single deep well plate.')
    bca_location = reagent_tubes[reagent_location]
    diluent_location = reagent_tubes[diluent_location]

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

    # check parameters and calculate the BCA reagent height, change in height per well loading, and diluent height
    reagent_h, reagent_delta_h, diluent_h = CheckParameters()

    # load the BCA reagent
    if aspirate_reagent:
        dispense_locations = [d['dispense location'] for d in datums]
        p300.pick_up_tip()
        p300.well_bottom_clearance.aspirate = reagent_h
        for well in dispense_locations:
            p300.aspirate(reagent_vol_perWell, bca_location)
            p300.touch_tip(radius=0.9, v_offset=-2)
            p300.dispense(reagent_vol_perWell, plate[well])
            p300.touch_tip(radius=0.9, v_offset=-2)
            reagent_h, reagent_vol = ChangeReagentHeightVolume(reagent_h, reagent_vol)
            p300.well_bottom_clearance.aspirate = reagent_h
        p300.drop_tip()

    # load the samples
    for i in range(len(datums)):
        p300.well_bottom_clearance.aspirate = sample_aspiration_height
        p20.well_bottom_clearance.aspirate = sample_aspiration_height
        sample_load_vol = sample_vol_perWell / float(datums[i]['dilution'])
        diluent_load_vol = sample_vol_perWell - sample_load_vol
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
            diluent_h, diluent_vol = ChangeDiluentHeightVolume(diluent_h, diluent_vol, diluent_load_vol)
            p300.well_bottom_clearance.aspirate = reagent_h
        elif diluent_load_vol > 0:
            p20.well_bottom_clearance.aspirate = diluent_h
            p20.pick_up_tip()
            p20.aspirate(diluent_load_vol, diluent_location)
            p20.touch_tip(radius=0.9, v_offset=-2)
            p20.dispense(diluent_load_vol, plate[datums[i]['dispense location']])
            p20.touch_tip(radius=0.9, v_offset=-2)
            p20.drop_tip()
            diluent_h, diluent_vol = ChangeDiluentHeightVolume(diluent_h, diluent_vol, diluent_load_vol)
            p20.well_bottom_clearance.aspirate = reagent_h

    protocol.set_rail_lights(False)  # turn the lights off