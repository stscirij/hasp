import numpy as np

GRATING_PRIORITIES = {'STIS/E140M': {'minwave': 1144, 'maxwave': 1710, 'priority': 1},
                      'COS/G130M': {'minwave': 900, 'maxwave': 1470, 'priority': 2},
                      'COS/G160M': {'minwave': 1342, 'maxwave': 1800, 'priority': 3},
                      'STIS/E140H': {'minwave': 1139, 'maxwave': 1700, 'priority': 4},
                      'STIS/G140M': {'minwave': 1140, 'maxwave': 1740, 'priority': 5},
                      'STIS/E230M': {'minwave': 1605, 'maxwave': 3110, 'priority': 6},
                      'STIS/E230H': {'minwave': 1620, 'maxwave': 3150, 'priority': 7},
                      'STIS/G230M': {'minwave': 1640, 'maxwave': 3100, 'priority': 8},
                      'COS/G140L': {'minwave': 901, 'maxwave': 2150, 'priority': 9},
                      'STIS/G230MB': {'minwave': 1641, 'maxwave': 3190, 'priority': 10},
                      'COS/G185M': {'minwave': 1664, 'maxwave': 2134, 'priority': 11},
                      'COS/G225M': {'minwave': 2069, 'maxwave': 2526, 'priority': 12},
                      'COS/G285M': {'minwave': 2474, 'maxwave': 3221, 'priority': 13},
                      'STIS/G140L': {'minwave': 1150, 'maxwave': 1730, 'priority': 14},
                      'STIS/G430M': {'minwave': 3020, 'maxwave': 5610, 'priority': 15},
                      'STIS/G230L': {'minwave': 1570, 'maxwave': 3180, 'priority': 16},
                      'STIS/G230LB': {'minwave': 1680, 'maxwave': 3060, 'priority': 17},
                      'COS/G230L': {'minwave': 1650, 'maxwave': 3200, 'priority': 18},
                      'STIS/G750M': {'minwave': 5450, 'maxwave': 10140, 'priority': 19},
                      'STIS/G430L': {'minwave': 2900, 'maxwave': 5700, 'priority': 20},
                      'STIS/G750L': {'minwave': 5240, 'maxwave': 10270, 'priority': 21},
}

def create_level4_products(productlist, productdict, producttype, uniqmodes, outdir):
    used_gratings_list = get_used_gratings(productlist)
    ngratings = len(used_gratings_list)
    if ngratings == 1:
        print("No need to make abutted product as only 1 grating")
        return None
    if ngratings == 0:
        print('No valid input grating products')
        return None
    print("Making a product from these gratings")
    for grating in used_gratings_list:
        actual_minwave = productdict[grating['name']].first_good_wavelength
        actual_maxwave = productdict[grating['name']].last_good_wavelength
        print(grating['name'], f"{grating['minwave']}-{grating['maxwave']}", '(Actual: {:.1f}-{:.1f})'.format(actual_minwave, actual_maxwave))
    score = 2 ** ngratings
    if ngratings > 0:
        for grating in used_gratings_list:
            grating['score'] = score
            score = score // 2
    transition_wavelengths = []
    for grating in used_gratings_list:
        actual_minwave = productdict[grating['name']].first_good_wavelength
        actual_maxwave = productdict[grating['name']].last_good_wavelength
        min_wavelength = max(actual_minwave, grating['minwave'])
        max_wavelength = min(actual_maxwave, grating['maxwave'])
        if min_wavelength != grating['minwave'] or max_wavelength != grating['maxwave']:
            print('Transition wavelengths tweaked')
        transition_wavelengths.append({'grating': grating['name'], 'wavelength': min_wavelength, 'delta': grating['score']})
        transition_wavelengths.append({'grating': grating['name'], 'wavelength': max_wavelength, 'delta': -grating['score']})
    transition_wavelengths = sorted(transition_wavelengths, key=lambda wavelength: wavelength['wavelength'])
    cumulative_sum = 0
    this_grating = None
    abutted_product = None
    nwavelengths = len(transition_wavelengths)
    for entry in range(nwavelengths):
        value = transition_wavelengths[entry]
        cumulative_sum = cumulative_sum + value['delta']
        highest_power_of_2 = hp2(cumulative_sum, ngratings)
        grating_rows = [row for row in used_gratings_list if row['score'] == highest_power_of_2]
        n_with_this_score = len(grating_rows)
        if n_with_this_score == 1:
            new_grating = grating_rows[0]['name']
        elif n_with_this_score == 0:
            new_grating = None
        else:
            print("Unexpected number of gratings with score {}: {}".format(highest_power_of_two, n_with_this_score))
            new_grating = "Error"
        if new_grating != this_grating:
            if abutted_product is None:
                print('Starting at the short wavelength end with grating {}'.format(new_grating))
                abutted_product = abut(None, productdict[new_grating], value['wavelength'])
            elif new_grating is None:
                print('Truncating current grating at {}'.format(value['wavelength']))
                abutted_product = abut(abutted_product, None, value['wavelength'])
            else:
                print('Abutting {} product to current result'.format(new_grating))
                print('With a transition wavelength of {}'.format(value['wavelength']))
                abutted_product = abut(abutted_product, productdict[new_grating], value['wavelength'])
            this_grating = new_grating
    return abutted_product

def get_used_gratings(productlist):
    used_gratings_list = []
    used_gratings_dict = {}
    for product in productlist:
        setting = product.instrument + '/' + product.grating
        if setting in GRATING_PRIORITIES:
            grating_dict = GRATING_PRIORITIES[setting]
            grating_dict['name'] = setting
            used_gratings_list.append(grating_dict)
            used_gratings_dict[setting] = grating_dict
    used_gratings_list = sorted(used_gratings_list, key=lambda grating: grating['priority'])
    return used_gratings_list

def hp2(number, largest_power):
    # Returns the highest power of 2 that is <= number, up to
    # and including 2**largest_power
    if number == 0: return 0
    for i in range(largest_power, 0, -1):
        if number & (2 ** i):
            break
    return 2 ** i

def abut(product_short, product_long, transition_wavelength):
    """Abut the spectra in 2 products.  Assumes the first argument is the shorter
    wavelength.
    """
    if product_short is not None and product_long is not None:
        if transition_wavelength == "bad":
            return None
        # Make sure the grating doesn't appear more than once in the filename
        if product_long.grating not in product_short.gratinglist:
            product_short.gratinglist.append(product_long.grating)
            output_grating = product_short.grating + '-' + product_long.disambiguated_grating
        else:
            output_grating = product_short.grating
        product_abutted = product_short.__class__('', output_grating)
        goodshort = np.where(product_short.output_exptime > 0.)
        goodlong = np.where(product_long.output_exptime > 0.)
        last_good_short = product_short.output_wavelength[goodshort][-1]
        first_good_long = product_long.output_wavelength[goodlong][0]
        short_indices = np.where(product_short.output_wavelength < last_good_short)
        transition_index_short = short_indices[0][-1]
        long_indices = np.where(product_long.output_wavelength > first_good_long)
        transition_index_long = long_indices[0][0]
        if transition_wavelength is not None:
            short_indices = np.where(product_short.output_wavelength <= transition_wavelength)
            if len(short_indices[0]) == 0:
                print('No valid data in short-wavelength spectrum')
                return product_long
            transition_index_short = short_indices[0][-1]
            long_indices = np.where(product_long.output_wavelength > transition_wavelength)
            if len(long_indices[0]) == 0:
                print('No valid data in long-wavelength spectrum')
                return product_short
            transition_index_long = long_indices[0][0]
        nout = len(product_short.output_wavelength[:transition_index_short])
        nout = nout + len(product_long.output_wavelength[transition_index_long:])
        product_abutted.nelements = nout
        product_abutted.output_wavelength = np.zeros(nout)
        product_abutted.output_flux = np.zeros(nout)
        product_abutted.output_errors = np.zeros(nout)
        product_abutted.signal_to_noise = np.zeros(nout)
        product_abutted.output_exptime = np.zeros(nout)
        product_abutted.setting = np.repeat(np.array(20*' ',dtype='str'), nout)
        product_abutted.output_wavelength[:transition_index_short] = product_short.output_wavelength[:transition_index_short]
        product_abutted.output_wavelength[transition_index_short:] = product_long.output_wavelength[transition_index_long:]
        product_abutted.output_flux[:transition_index_short] = product_short.output_flux[:transition_index_short]
        product_abutted.output_flux[transition_index_short:] = product_long.output_flux[transition_index_long:]
        product_abutted.output_errors[:transition_index_short] = np.abs(product_short.output_errors[:transition_index_short])
        product_abutted.output_errors[transition_index_short:] = np.abs(product_long.output_errors[transition_index_long:])
        product_abutted.signal_to_noise[:transition_index_short] = product_short.signal_to_noise[:transition_index_short]
        product_abutted.signal_to_noise[transition_index_short:] = product_long.signal_to_noise[transition_index_long:]
        product_abutted.output_exptime[:transition_index_short] = product_short.output_exptime[:transition_index_short]
        product_abutted.output_exptime[transition_index_short:] = product_long.output_exptime[transition_index_long:]
        product_abutted.setting[:transition_index_short] = product_short.setting[:transition_index_short]
        product_abutted.setting[transition_index_short:] = product_long.setting[transition_index_long:]
        product_abutted.primary_headers = product_short.primary_headers + product_long.primary_headers
        product_abutted.first_headers = product_short.first_headers + product_long.first_headers
        product_abutted.grating = output_grating
        product_abutted.disambiguated_grating = output_grating
        product_abutted.gratinglist = product_short.gratinglist
        product_short.target = product_short.get_targname()
        product_long.target = product_long.get_targname()
        if product_short.instrument in product_long.instrument:
            product_abutted.instrument = product_long.instrument
        if product_long.instrument in product_short.instrument:
            product_abutted.instrument = product_short.instrument
        else:
            product_abutted.instrument = product_short.instrument + '-' + product_long.instrument
        target_matched = False
        if product_short.target == product_long.target:
            product_abutted.target = product_short.target
            target_matched = True
            product_abutted.targnames = [product_short.target, product_long.target]
        else:
            for target_name in product_short.targnames:
                if target_name in product_long.targnames:
                    product_abutted.target = product_abutted.get_targname()
                    target_matched = True
                    product_abutted.targnames = [target_name]
        if not target_matched:
            product_abutted = None
            print(f'Trying to abut spectra from 2 different targets:')
            print(f'{product_short.target} and {product_long.target}')
        product_abutted.propid = product_short.propid
        product_abutted.rootname = product_short.rootname
    elif product_short is not None:
        # This will be the case for the last grating
        output_grating = product_short.grating
        product_abutted = product_short.__class__('', output_grating)
        short_indices = np.where(product_short.output_wavelength < transition_wavelength)
        transition_index_short = short_indices[0][-1]
        nout = len(product_short.output_wavelength[:transition_index_short])
        product_abutted.nelements = nout
        product_abutted.output_wavelength = np.zeros(nout)
        product_abutted.output_flux = np.zeros(nout)
        product_abutted.output_errors = np.zeros(nout)
        product_abutted.signal_to_noise = np.zeros(nout)
        product_abutted.output_exptime = np.zeros(nout)
        product_abutted.setting = np.zeros(nout)
        product_abutted.output_wavelength = product_short.output_wavelength[:transition_index_short]
        product_abutted.output_flux = product_short.output_flux[:transition_index_short]
        product_abutted.output_errors = np.abs(product_short.output_errors[:transition_index_short])
        product_abutted.signal_to_noise = product_short.signal_to_noise[:transition_index_short]
        product_abutted.output_exptime = product_short.output_exptime[:transition_index_short]
        product_abutted.setting = product_short.setting[:transition_index_short]
        product_abutted.primary_headers = product_short.primary_headers
        product_abutted.first_headers = product_short.first_headers
        product_abutted.grating = product_short.grating
        product_abutted.disambiguated_grating = product_short.disambiguated_grating
        product_abutted.gratinglist = product_short.gratinglist
        product_abutted.instrument = product_short.instrument
        product_abutted.target = product_short.target
        target_matched = True
        product_abutted.targnames = [product_short.target]
        product_abutted.propid = product_short.propid
        product_abutted.rootname = product_short.rootname
    elif product_long is not None:
        # This is the case for the first grating
        output_grating = product_long.disambiguated_grating
        product_abutted = product_long.__class__('', output_grating)
        long_indices = np.where(product_long.output_wavelength > transition_wavelength)
        transition_index_long = long_indices[0][0]
        nout = len(product_long.output_wavelength[transition_index_long:])
        product_abutted.nelements = nout
        product_abutted.output_wavelength = np.zeros(nout)
        product_abutted.output_flux = np.zeros(nout)
        product_abutted.output_errors = np.zeros(nout)
        product_abutted.signal_to_noise = np.zeros(nout)
        product_abutted.output_exptime = np.zeros(nout)
        product_abutted.settimg = np.zeros(nout)
        product_abutted.output_wavelength = product_long.output_wavelength[transition_index_long:]
        product_abutted.output_flux = product_long.output_flux[transition_index_long:]
        product_abutted.output_errors = np.abs(product_long.output_errors[transition_index_long:])
        product_abutted.signal_to_noise = product_long.signal_to_noise[transition_index_long:]
        product_abutted.output_exptime = product_long.output_exptime[transition_index_long:]
        product_abutted.setting = product_long.setting[transition_index_long:]
        product_abutted.primary_headers = product_long.primary_headers
        product_abutted.first_headers = product_long.first_headers
        product_abutted.grating = product_long.disambiguated_grating
        product_abutted.disambiguated_grating = product_long.disambiguated_grating
        product_abutted.gratinglist = product_long.gratinglist
        product_long.target = product_long.get_targname()
        product_abutted.instrument = product_long.instrument
        product_abutted.target = product_long.target
        target_matched = True
        product_abutted.targnames = [product_long.target]
        product_abutted.propid = product_long.propid
        product_abutted.rootname = product_long.rootname
    else:
        product_abutted = None
    product_abutted.targ_ra, product_abutted.targ_dec = product_abutted.get_coords()
    return product_abutted
