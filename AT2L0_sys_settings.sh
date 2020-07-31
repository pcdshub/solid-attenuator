#!/bin/bash

PREFIX=${PREFIX:=AT2L0:SIM}

caput ${PREFIX}:FILTER:02:Material "C"
caput ${PREFIX}:FILTER:03:Material "C"
caput ${PREFIX}:FILTER:04:Material "C"
caput ${PREFIX}:FILTER:05:Material "C"
caput ${PREFIX}:FILTER:06:Material "C"
caput ${PREFIX}:FILTER:07:Material "C"
caput ${PREFIX}:FILTER:08:Material "C"
caput ${PREFIX}:FILTER:09:Material "C"
caput ${PREFIX}:FILTER:10:Material "Si"
caput ${PREFIX}:FILTER:11:Material "Si"
caput ${PREFIX}:FILTER:12:Material "Si"
caput ${PREFIX}:FILTER:13:Material "Si"
caput ${PREFIX}:FILTER:14:Material "Si"
caput ${PREFIX}:FILTER:15:Material "Si"
caput ${PREFIX}:FILTER:16:Material "Si"
caput ${PREFIX}:FILTER:17:Material "Si"
caput ${PREFIX}:FILTER:18:Material "Si"
caput ${PREFIX}:FILTER:19:Material "Si"

caput ${PREFIX}:FILTER:02:Thickness "1280"
caput ${PREFIX}:FILTER:03:Thickness "320"
caput ${PREFIX}:FILTER:04:Thickness "640"
caput ${PREFIX}:FILTER:05:Thickness "160"
caput ${PREFIX}:FILTER:06:Thickness "80"
caput ${PREFIX}:FILTER:07:Thickness "40"
caput ${PREFIX}:FILTER:08:Thickness "20"
caput ${PREFIX}:FILTER:09:Thickness "10"
caput ${PREFIX}:FILTER:10:Thickness "10240"
caput ${PREFIX}:FILTER:11:Thickness "5120"
caput ${PREFIX}:FILTER:12:Thickness "2560"
caput ${PREFIX}:FILTER:13:Thickness "1280"
caput ${PREFIX}:FILTER:14:Thickness "640"
caput ${PREFIX}:FILTER:15:Thickness "320"
caput ${PREFIX}:FILTER:16:Thickness "160"
caput ${PREFIX}:FILTER:17:Thickness "80"
caput ${PREFIX}:FILTER:18:Thickness "40"
caput ${PREFIX}:FILTER:19:Thickness "20"

caput ${PREFIX}:FILTER:02:IsStuck 0
caput ${PREFIX}:FILTER:03:IsStuck 0
caput ${PREFIX}:FILTER:04:IsStuck 0
caput ${PREFIX}:FILTER:05:IsStuck 0
caput ${PREFIX}:FILTER:06:IsStuck 0
caput ${PREFIX}:FILTER:07:IsStuck 0
caput ${PREFIX}:FILTER:08:IsStuck 0
caput ${PREFIX}:FILTER:09:IsStuck 0
caput ${PREFIX}:FILTER:10:IsStuck 0
caput ${PREFIX}:FILTER:11:IsStuck 0
caput ${PREFIX}:FILTER:12:IsStuck 0
caput ${PREFIX}:FILTER:13:IsStuck 0
caput ${PREFIX}:FILTER:14:IsStuck 0
caput ${PREFIX}:FILTER:15:IsStuck 0
caput ${PREFIX}:FILTER:16:IsStuck 0
caput ${PREFIX}:FILTER:17:IsStuck 0
caput ${PREFIX}:FILTER:18:IsStuck 0
caput ${PREFIX}:FILTER:19:IsStuck 0

caput ${PREFIX}:SYS:Run 0
