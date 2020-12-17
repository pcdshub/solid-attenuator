Filter Selection Information
----------------------------

Best Configuration Algorithm
============================

The generic "best configuration" algorithm ``get_best_config`` does its best to
choose the right filters to target the requested transmission.

It does this by enumerating all possible filter configurations, doing a matrix
multiplication to determine the transmission values for all of those
configurations. Figuring out the best configuration is then a matter of
matching the closest transmission value (i.e., `argmin(abs(all_transmissions -
target_transmission))`.  This makes no assumptions as to how the filters are
laid out and is as generic as possible.

Now, if all filters of every material type are used with the above algorithm,
some silicon filters may be inserted prior to diamond filters. This is not
good, as the silicon filters may be damaged. We need a new algorithm to get
around that.

Material-prioritizing Algorithm
===============================

This section uses AT2L0 as an example, with 8 diamond filters and 10 silicon
filters.  The desire here is to have all diamond filters inserted prior to
inserting any silicon filters.

The algorithm behind ``get_best_config_with_material_priority`` breaks up
the problem into 2 calls to the original algorithm, once per material.

For AT2L0, with a desired transmission of ``t_des``,

1. Apply the original algorithm _only_ for the diamond filters. Due to how the
   filters are physically configured, the diamond filters can get very close to
   the required transmission up to a certain value (`t_all_diamond_inserted` to
   `1.0`). This works because the filter thicknesses were carefully specified:
   each filter is 2x the previous filter in thickness.

    As an aside, this means you could treat each filter as binary value,
    spanning the range  ``t_all_diamond_inserted <= t_des <= 1.0`` in
    2^num_filters = 2^8 steps (i.e., ``(1 - t_all_diamond_inserted) / 2 ** 8``,
    which is ``< 0.4%`` per step)

    Let's call the result from step (1) a transmission value of ``transmission_1``.

2. Now,

    a. For desired transmission within
       ``t_all_diamond_inserted <= t_des <= 1.0``, the algorithm will have
       pretty much gotten the requested transmission as close as needed. The
       algorithm will have chosen the "floor" configuration, favoring going
       under the desired transmission. This is important for a possible future
       scenario where any diamond filters are out of commission (stuck in the
       out position due to hardware failure, damaged, etc).
    b. For desired transmission ``0 <= t_des < t_all_diamond_inserted``, the
       algorithm will have already selected all diamond filters. There's more
       left to do in the second round as we can still get closer to ``t_des``,
       when calculating which silicon filters to insert.

3. As normalized transmission values are multiplicative (50% of 50%
   transmission would be 25%), our second round tries to find the right
   configuration of silicon filters for ``t_des / transmission_1``.

   a. For values in the range noted by (2a), ``t_des / transmission1`` will be
      close to 1 - so no filters will be inserted.
   b. For values in the range noted by (2b), ``t_des / transmission1`` will
      likely be something actionable.

4. Assembling the two configurations from (1) and (3) gives a final configuration, specifying all filter states.


Ladder-style algorithm
======================

This is not yet implemented.

ESD reference
=============

According to the ESD (LCLSII-3.5-ES-0267-R1, page 8)::

    Diamond filters shall always be used when the silicon filters are in the beam
    (pre-filtering) per Figure 4.

Page 11::

    Diamond filter(s) shall always be used to provide attenuation
    (pre-filtering) when silicon filters are used. The required attenuation and
    diamond filter thicknesses for pre-filtering the silicon filters in the 6 –
    25 keV range is shown in Figure 4.

Page 15::

    When operating in the Cu-HXR mode, the MPS shall ensure that:
    [...]
    * The appropriate diamond pre-filter is inserted prior to inserting a silicon filter,
