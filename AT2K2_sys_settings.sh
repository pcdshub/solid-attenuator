#!/bin/bash

echo "To set production settings, use PREFIX=AT2K2:CALC bash $0"

PREFIX=${PREFIX:=AT2K2:SIM}

echo "Prefix set to: $PREFIX"

set -e

# Corresponds to MMS:01 -> most upstream axis
# AT2K2 	SN-11343 	1087
caput ${PREFIX}:AXIS:01:IsStuck 0

caput ${PREFIX}:AXIS:01:FILTER:01:Material "Al"  # Not active
caput ${PREFIX}:AXIS:01:FILTER:02:Material "Al"  # Not active
caput ${PREFIX}:AXIS:01:FILTER:03:Material "Al"  # Not active
caput ${PREFIX}:AXIS:01:FILTER:04:Material "Al"  # Not active
caput ${PREFIX}:AXIS:01:FILTER:05:Material "Al"
caput ${PREFIX}:AXIS:01:FILTER:06:Material "Al"
caput ${PREFIX}:AXIS:01:FILTER:07:Material "Al"
caput ${PREFIX}:AXIS:01:FILTER:08:Material "Al"

caput ${PREFIX}:AXIS:01:FILTER:01:Thickness "0"  # Not active
caput ${PREFIX}:AXIS:01:FILTER:02:Thickness "0"  # Not active
caput ${PREFIX}:AXIS:01:FILTER:03:Thickness "0"  # Not active
caput ${PREFIX}:AXIS:01:FILTER:04:Thickness "0"  # Not active
caput ${PREFIX}:AXIS:01:FILTER:05:Thickness "1.52"
caput ${PREFIX}:AXIS:01:FILTER:06:Thickness "2.85"
caput ${PREFIX}:AXIS:01:FILTER:07:Thickness "6.18"
caput ${PREFIX}:AXIS:01:FILTER:08:Thickness "11.5"

caput ${PREFIX}:AXIS:01:FILTER:01:Active "False" # Not active
caput ${PREFIX}:AXIS:01:FILTER:02:Active "False" # Not active
caput ${PREFIX}:AXIS:01:FILTER:03:Active "False" # Not active
caput ${PREFIX}:AXIS:01:FILTER:04:Active "False" # Not active
caput ${PREFIX}:AXIS:01:FILTER:05:Active "True"
caput ${PREFIX}:AXIS:01:FILTER:06:Active "True"
caput ${PREFIX}:AXIS:01:FILTER:07:Active "True"
caput ${PREFIX}:AXIS:01:FILTER:08:Active "True"

# MMS:02
# AT2K2 	SN-11343 	1088
caput ${PREFIX}:AXIS:02:IsStuck 0

caput ${PREFIX}:AXIS:02:FILTER:01:Material "Al"  # not active
caput ${PREFIX}:AXIS:02:FILTER:02:Material "Al"  # not active
caput ${PREFIX}:AXIS:02:FILTER:03:Material "Al"  # not active
caput ${PREFIX}:AXIS:02:FILTER:04:Material "Al"  # not active
caput ${PREFIX}:AXIS:02:FILTER:05:Material "Al"
caput ${PREFIX}:AXIS:02:FILTER:06:Material "Al"
caput ${PREFIX}:AXIS:02:FILTER:07:Material "Al"
caput ${PREFIX}:AXIS:02:FILTER:08:Material "Al"

caput ${PREFIX}:AXIS:02:FILTER:01:Thickness "0"  # not active
caput ${PREFIX}:AXIS:02:FILTER:02:Thickness "0"  # not active
caput ${PREFIX}:AXIS:02:FILTER:03:Thickness "0"  # not active
caput ${PREFIX}:AXIS:02:FILTER:04:Thickness "0"  # not active
caput ${PREFIX}:AXIS:02:FILTER:05:Thickness "0.78"
caput ${PREFIX}:AXIS:02:FILTER:06:Thickness "1.52"
caput ${PREFIX}:AXIS:02:FILTER:07:Thickness "2.85"
caput ${PREFIX}:AXIS:02:FILTER:08:Thickness "6.18"

caput ${PREFIX}:AXIS:02:FILTER:01:Active "False"  # not active
caput ${PREFIX}:AXIS:02:FILTER:02:Active "False"  # not active
caput ${PREFIX}:AXIS:02:FILTER:03:Active "False"  # not active
caput ${PREFIX}:AXIS:02:FILTER:04:Active "False"  # not active
caput ${PREFIX}:AXIS:02:FILTER:05:Active "True"
caput ${PREFIX}:AXIS:02:FILTER:06:Active "True"
caput ${PREFIX}:AXIS:02:FILTER:07:Active "True"
caput ${PREFIX}:AXIS:02:FILTER:08:Active "True"

# MMS:03 -> 2nd to upstream axis
# AT1K4 	SN-11343 	1086
caput ${PREFIX}:AXIS:03:IsStuck 0

caput ${PREFIX}:AXIS:03:FILTER:01:Material "Al"  # not active
caput ${PREFIX}:AXIS:03:FILTER:02:Material "Al"  # not active
caput ${PREFIX}:AXIS:03:FILTER:03:Material "Al"  # not active
caput ${PREFIX}:AXIS:03:FILTER:04:Material "Al"  # not active
caput ${PREFIX}:AXIS:03:FILTER:05:Material "Al"
caput ${PREFIX}:AXIS:03:FILTER:06:Material "Al"
caput ${PREFIX}:AXIS:03:FILTER:07:Material "Al"
caput ${PREFIX}:AXIS:03:FILTER:08:Material "Al"

caput ${PREFIX}:AXIS:03:FILTER:01:Thickness "0"  # not active
caput ${PREFIX}:AXIS:03:FILTER:02:Thickness "0"  # not active
caput ${PREFIX}:AXIS:03:FILTER:03:Thickness "0"  # not active
caput ${PREFIX}:AXIS:03:FILTER:04:Thickness "0"  # not active
caput ${PREFIX}:AXIS:03:FILTER:05:Thickness "0.39"
caput ${PREFIX}:AXIS:03:FILTER:06:Thickness "0.78"
caput ${PREFIX}:AXIS:03:FILTER:07:Thickness "1.52"
caput ${PREFIX}:AXIS:03:FILTER:08:Thickness "2.85"

caput ${PREFIX}:AXIS:03:FILTER:01:Active "False"  # not active
caput ${PREFIX}:AXIS:03:FILTER:02:Active "False"  # not active
caput ${PREFIX}:AXIS:03:FILTER:03:Active "False"  # not active
caput ${PREFIX}:AXIS:03:FILTER:04:Active "False"  # not active
caput ${PREFIX}:AXIS:03:FILTER:05:Active "True"
caput ${PREFIX}:AXIS:03:FILTER:06:Active "True"
caput ${PREFIX}:AXIS:03:FILTER:07:Active "True"
caput ${PREFIX}:AXIS:03:FILTER:08:Active "True"

# MMS:04 -> upstream-most axis
# AT1K4 	SN-11343 	1089
caput ${PREFIX}:AXIS:04:IsStuck 0

caput ${PREFIX}:AXIS:04:FILTER:01:Material "Al"  # not active
caput ${PREFIX}:AXIS:04:FILTER:02:Material "Al"  # not active
caput ${PREFIX}:AXIS:04:FILTER:03:Material "Al"  # not active
caput ${PREFIX}:AXIS:04:FILTER:04:Material "Al"  # not active
caput ${PREFIX}:AXIS:04:FILTER:05:Material "Al"
caput ${PREFIX}:AXIS:04:FILTER:06:Material "Al"
caput ${PREFIX}:AXIS:04:FILTER:07:Material "Al"
caput ${PREFIX}:AXIS:04:FILTER:08:Material "Al"

caput ${PREFIX}:AXIS:04:FILTER:01:Thickness "0"  # not active
caput ${PREFIX}:AXIS:04:FILTER:02:Thickness "0"  # not active
caput ${PREFIX}:AXIS:04:FILTER:03:Thickness "0"  # not active
caput ${PREFIX}:AXIS:04:FILTER:04:Thickness "0"  # not active
caput ${PREFIX}:AXIS:04:FILTER:05:Thickness "0.20"
caput ${PREFIX}:AXIS:04:FILTER:06:Thickness "0.39"
caput ${PREFIX}:AXIS:04:FILTER:07:Thickness "0.78"
caput ${PREFIX}:AXIS:04:FILTER:08:Thickness "1.52"

caput ${PREFIX}:AXIS:04:FILTER:01:Active "False"  # not active
caput ${PREFIX}:AXIS:04:FILTER:02:Active "False"  # not active
caput ${PREFIX}:AXIS:04:FILTER:03:Active "False"  # not active
caput ${PREFIX}:AXIS:04:FILTER:04:Active "False"  # not active
caput ${PREFIX}:AXIS:04:FILTER:05:Active "True"
caput ${PREFIX}:AXIS:04:FILTER:06:Active "True"
caput ${PREFIX}:AXIS:04:FILTER:07:Active "True"
caput ${PREFIX}:AXIS:04:FILTER:08:Active "True"

caput ${PREFIX}:SYS:Run 0
