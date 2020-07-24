all: configs.h5 absorption_data.h5

absorption_data.h5: data_conditioner.py CXRO/*.nff 
	python data_conditioner.py $@
	@echo "Successfully created $@"

configs.h5: configurations.py
	python configurations.py inout 18 $@
	@echo "Successfully created $@"

clean:
	rm -f configs.h5 absorption_data.h5

.PHONY: all clean
