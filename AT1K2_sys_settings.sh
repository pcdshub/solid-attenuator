#!/bin/bash

echo "To set production settings, use PREFIX=AT1K2:CALC bash $0"

PREFIX=${PREFIX:=AT1K2:SIM}

echo "Prefix set to: $PREFIX"

set -e

# Corresponds to MMS:01 -> most upstream axis
# AT1K2 	SN-11343
caput ${PREFIX}:AXIS:01:IsStuck 0

caput ${PREFIX}:AXIS:01:FILTER:01:Material "Al"  # Not active
caput ${PREFIX}:AXIS:01:FILTER:02:Material "Al"  # Not active
caput ${PREFIX}:AXIS:01:FILTER:03:Material "Al"
caput ${PREFIX}:AXIS:01:FILTER:04:Material "Al"
caput ${PREFIX}:AXIS:01:FILTER:05:Material "Al"
caput ${PREFIX}:AXIS:01:FILTER:06:Material "Al"
caput ${PREFIX}:AXIS:01:FILTER:07:Material "Al"
caput ${PREFIX}:AXIS:01:FILTER:08:Material "Al"

caput ${PREFIX}:AXIS:01:FILTER:01:Thickness "0"  # Not active
caput ${PREFIX}:AXIS:01:FILTER:02:Thickness "0"  # Not active
caput ${PREFIX}:AXIS:01:FILTER:03:Thickness "11.5"
caput ${PREFIX}:AXIS:01:FILTER:04:Thickness "6.18"
caput ${PREFIX}:AXIS:01:FILTER:05:Thickness "2.85"
caput ${PREFIX}:AXIS:01:FILTER:06:Thickness "1.52"
caput ${PREFIX}:AXIS:01:FILTER:07:Thickness "0.78"
caput ${PREFIX}:AXIS:01:FILTER:08:Thickness "0.39"

caput ${PREFIX}:AXIS:01:FILTER:01:Active "False" # Not active
caput ${PREFIX}:AXIS:01:FILTER:02:Active "False" # Not active
caput ${PREFIX}:AXIS:01:FILTER:03:Active "True"
caput ${PREFIX}:AXIS:01:FILTER:04:Active "True"
caput ${PREFIX}:AXIS:01:FILTER:05:Active "True"
caput ${PREFIX}:AXIS:01:FILTER:06:Active "True"
caput ${PREFIX}:AXIS:01:FILTER:07:Active "True"
caput ${PREFIX}:AXIS:01:FILTER:08:Active "True"

# MMS:02
# AT1K2 	SN-11343
caput ${PREFIX}:AXIS:02:IsStuck 0

caput ${PREFIX}:AXIS:02:FILTER:01:Material "Al"  # not active
caput ${PREFIX}:AXIS:02:FILTER:02:Material "Al"  # not active
caput ${PREFIX}:AXIS:02:FILTER:03:Material "Al"
caput ${PREFIX}:AXIS:02:FILTER:04:Material "Al"
caput ${PREFIX}:AXIS:02:FILTER:05:Material "Al"
caput ${PREFIX}:AXIS:02:FILTER:06:Material "Al"
caput ${PREFIX}:AXIS:02:FILTER:07:Material "Al"
caput ${PREFIX}:AXIS:02:FILTER:08:Material "Al"

caput ${PREFIX}:AXIS:02:FILTER:01:Thickness "0"  # not active
caput ${PREFIX}:AXIS:02:FILTER:02:Thickness "0"  # not active
caput ${PREFIX}:AXIS:02:FILTER:03:Thickness "11.5"
caput ${PREFIX}:AXIS:02:FILTER:04:Thickness "6.18"
caput ${PREFIX}:AXIS:02:FILTER:05:Thickness "1.52"
caput ${PREFIX}:AXIS:02:FILTER:06:Thickness "0.78"
caput ${PREFIX}:AXIS:02:FILTER:07:Thickness "0.39"
caput ${PREFIX}:AXIS:02:FILTER:08:Thickness "0.2"

caput ${PREFIX}:AXIS:02:FILTER:01:Active "False"  # not active
caput ${PREFIX}:AXIS:02:FILTER:02:Active "False"  # not active
caput ${PREFIX}:AXIS:02:FILTER:03:Active "True"
caput ${PREFIX}:AXIS:02:FILTER:04:Active "True"
caput ${PREFIX}:AXIS:02:FILTER:05:Active "True"
caput ${PREFIX}:AXIS:02:FILTER:06:Active "True"
caput ${PREFIX}:AXIS:02:FILTER:07:Active "True"
caput ${PREFIX}:AXIS:02:FILTER:08:Active "True"

caput ${PREFIX}:SYS:Run 0
