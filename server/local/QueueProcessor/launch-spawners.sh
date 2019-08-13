#!/bin/bash
for x in $(seq 1 $1) do
        rq worker --url redis://windows/1 pluto & disown
done
