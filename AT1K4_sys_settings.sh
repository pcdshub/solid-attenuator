#!/bin/bash

echo "To set production settings, use PREFIX=AT1K4:CALC bash $0"

PREFIX=${PREFIX:=AT1K4:SIM}

echo "Prefix set to: $PREFIX"

set -e

# Corresponds to MMS:01 -> most upstream axis
# AT1K4 	SN-11345 	1072
caput ${PREFIX}:AXIS:01:IsStuck 0

caput ${PREFIX}:AXIS:01:Filter:01:Material "C"
caput ${PREFIX}:AXIS:01:Filter:02:Material "C"
caput ${PREFIX}:AXIS:01:Filter:03:Material "C"
caput ${PREFIX}:AXIS:01:Filter:04:Material "Si"
caput ${PREFIX}:AXIS:01:Filter:05:Material "Si"
caput ${PREFIX}:AXIS:01:Filter:06:Material "Si"
caput ${PREFIX}:AXIS:01:Filter:07:Material "Si"
caput ${PREFIX}:AXIS:01:Filter:08:Material "Si"

caput ${PREFIX}:AXIS:01:Filter:01:Thickness "25"
caput ${PREFIX}:AXIS:01:Filter:02:Thickness "50"
caput ${PREFIX}:AXIS:01:Filter:03:Thickness "100"
caput ${PREFIX}:AXIS:01:Filter:04:Thickness "320"
caput ${PREFIX}:AXIS:01:Filter:05:Thickness "160"
caput ${PREFIX}:AXIS:01:Filter:06:Thickness "80"
caput ${PREFIX}:AXIS:01:Filter:07:Thickness "40"
caput ${PREFIX}:AXIS:01:Filter:08:Thickness "20"

caput ${PREFIX}:AXIS:01:Filter:01:Active "True"
caput ${PREFIX}:AXIS:01:Filter:02:Active "True"
caput ${PREFIX}:AXIS:01:Filter:03:Active "True"
caput ${PREFIX}:AXIS:01:Filter:04:Active "True"
caput ${PREFIX}:AXIS:01:Filter:05:Active "True"
caput ${PREFIX}:AXIS:01:Filter:06:Active "True"
caput ${PREFIX}:AXIS:01:Filter:07:Active "True"
caput ${PREFIX}:AXIS:01:Filter:08:Active "True"

# MMS:02 -> 2nd-most upstream axis
# AT1K4 	SN-11345 	1084
caput ${PREFIX}:AXIS:02:IsStuck 0

caput ${PREFIX}:AXIS:02:Filter:01:Material "Si"  # not active
caput ${PREFIX}:AXIS:02:Filter:02:Material "Si"  # not active
caput ${PREFIX}:AXIS:02:Filter:03:Material "Si"  # not active
caput ${PREFIX}:AXIS:02:Filter:04:Material "Si"  # not active
caput ${PREFIX}:AXIS:02:Filter:05:Material "C"
caput ${PREFIX}:AXIS:02:Filter:06:Material "C"
caput ${PREFIX}:AXIS:02:Filter:07:Material "C"
caput ${PREFIX}:AXIS:02:Filter:08:Material "Si"

caput ${PREFIX}:AXIS:02:Filter:01:Thickness "0"  # not active
caput ${PREFIX}:AXIS:02:Filter:02:Thickness "0"  # not active
caput ${PREFIX}:AXIS:02:Filter:03:Thickness "0"  # not active
caput ${PREFIX}:AXIS:02:Filter:04:Thickness "0"  # not active
caput ${PREFIX}:AXIS:02:Filter:05:Thickness "50"
caput ${PREFIX}:AXIS:02:Filter:06:Thickness "25"
caput ${PREFIX}:AXIS:02:Filter:07:Thickness "12"
caput ${PREFIX}:AXIS:02:Filter:08:Thickness "10"

caput ${PREFIX}:AXIS:02:Filter:01:Active "False"  # not active
caput ${PREFIX}:AXIS:02:Filter:02:Active "False"  # not active
caput ${PREFIX}:AXIS:02:Filter:03:Active "False"  # not active
caput ${PREFIX}:AXIS:02:Filter:04:Active "False"  # not active
caput ${PREFIX}:AXIS:02:Filter:05:Active "True"
caput ${PREFIX}:AXIS:02:Filter:06:Active "True"
caput ${PREFIX}:AXIS:02:Filter:07:Active "True"
caput ${PREFIX}:AXIS:02:Filter:08:Active "True"

# MMS:03 -> 2nd to downstream axis
# AT1K4 	SN-11345 	1070
caput ${PREFIX}:AXIS:03:IsStuck 0

caput ${PREFIX}:AXIS:03:Filter:01:Material "Si"  # not active
caput ${PREFIX}:AXIS:03:Filter:02:Material "Si"  # not active
caput ${PREFIX}:AXIS:03:Filter:03:Material "Si"  # not active
caput ${PREFIX}:AXIS:03:Filter:04:Material "Si"  # not active
caput ${PREFIX}:AXIS:03:Filter:05:Material "Si"  # not active
caput ${PREFIX}:AXIS:03:Filter:06:Material "C"
caput ${PREFIX}:AXIS:03:Filter:07:Material "C"
caput ${PREFIX}:AXIS:03:Filter:08:Material "C"

caput ${PREFIX}:AXIS:03:Filter:01:Thickness "0"  # not active
caput ${PREFIX}:AXIS:03:Filter:02:Thickness "0"  # not active
caput ${PREFIX}:AXIS:03:Filter:03:Thickness "0"  # not active
caput ${PREFIX}:AXIS:03:Filter:04:Thickness "0"  # not active
caput ${PREFIX}:AXIS:03:Filter:05:Thickness "0"  # not active
caput ${PREFIX}:AXIS:03:Filter:06:Thickness "25"
caput ${PREFIX}:AXIS:03:Filter:07:Thickness "12"
caput ${PREFIX}:AXIS:03:Filter:08:Thickness "6"

caput ${PREFIX}:AXIS:03:Filter:01:Active "False"  # not active
caput ${PREFIX}:AXIS:03:Filter:02:Active "False"  # not active
caput ${PREFIX}:AXIS:03:Filter:03:Active "False"  # not active
caput ${PREFIX}:AXIS:03:Filter:04:Active "False"  # not active
caput ${PREFIX}:AXIS:03:Filter:05:Active "False"  # not active
caput ${PREFIX}:AXIS:03:Filter:06:Active "True"
caput ${PREFIX}:AXIS:03:Filter:07:Active "True"
caput ${PREFIX}:AXIS:03:Filter:08:Active "True"

# MMS:04 -> downstream-most axis
# AT1K4 	SN-11345 	1085
caput ${PREFIX}:AXIS:04:IsStuck 0

caput ${PREFIX}:AXIS:04:Filter:01:Material "Si"  # not active
caput ${PREFIX}:AXIS:04:Filter:02:Material "Si"  # not active
caput ${PREFIX}:AXIS:04:Filter:03:Material "Si"  # not active
caput ${PREFIX}:AXIS:04:Filter:04:Material "C"
caput ${PREFIX}:AXIS:04:Filter:05:Material "C"
caput ${PREFIX}:AXIS:04:Filter:06:Material "C"
caput ${PREFIX}:AXIS:04:Filter:07:Material "C"
caput ${PREFIX}:AXIS:04:Filter:08:Material "Al"

caput ${PREFIX}:AXIS:04:Filter:01:Thickness "0"  # not active
caput ${PREFIX}:AXIS:04:Filter:02:Thickness "0"  # not active
caput ${PREFIX}:AXIS:04:Filter:03:Thickness "0"  # not active
caput ${PREFIX}:AXIS:04:Filter:04:Thickness "12"
caput ${PREFIX}:AXIS:04:Filter:05:Thickness "6"
caput ${PREFIX}:AXIS:04:Filter:06:Thickness "3"
caput ${PREFIX}:AXIS:04:Filter:07:Thickness "3"
caput ${PREFIX}:AXIS:04:Filter:08:Thickness "0.2"

caput ${PREFIX}:AXIS:04:Filter:01:Active "False"  # not active
caput ${PREFIX}:AXIS:04:Filter:02:Active "False"  # not active
caput ${PREFIX}:AXIS:04:Filter:03:Active "False"  # not active
caput ${PREFIX}:AXIS:04:Filter:04:Active "True"
caput ${PREFIX}:AXIS:04:Filter:05:Active "True"
caput ${PREFIX}:AXIS:04:Filter:06:Active "True"
caput ${PREFIX}:AXIS:04:Filter:07:Active "True"
caput ${PREFIX}:AXIS:04:Filter:08:Active "True"

caput ${PREFIX}:SYS:Run 0
