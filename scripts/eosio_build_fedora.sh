	OS_VER=$( cat /etc/os-release | grep VERSION_ID | cut -d'=' -f2 | sed 's/[^0-9\.]//gI' )

	MEM_MEG=$( free -m | grep Mem | tr -s ' ' | cut -d\  -f2 )

	CPU_SPEED=$( lscpu | grep "MHz" | tr -s ' ' | cut -d\  -f3 | cut -d'.' -f1 )
	CPU_CORE=$( lscpu | grep "^CPU(s)" | tr -s ' ' | cut -d\  -f2 )

	DISK_TOTAL=`df -h / | grep /dev | tr -s ' ' | cut -d\  -f2 | sed 's/[^0-9]//'`
	DISK_AVAIL=`df -h / | grep /dev | tr -s ' ' | cut -d\  -f4 | sed 's/[^0-9]//'`

	printf "\n\tOS name: $OS_NAME\n"
	printf "\tOS Version: ${OS_VER}\n"
	printf "\tCPU speed: ${CPU_SPEED}Mhz\n"
	printf "\tCPU cores: $CPU_CORE\n"
	printf "\tPhysical Memory: $MEM_MEG Mgb\n"
	printf "\tDisk space total: ${DISK_TOTAL}G\n"
	printf "\tDisk space available: ${DISK_AVAIL}G\n"

	if [ $MEM_MEG -lt 4000 ]; then
		echo "Your system must have 8 or more Gigabytes of physical memory installed."
		echo "exiting now."
		exit 1
	fi

	if [ $OS_VER -lt 25 ]; then
		echo "You must be running Fedora 25 or higher to install EOSIO."
		echo "exiting now"
		exit 1
	fi

	if [ $DISK_AVAIL -lt 100 ]; then
		echo "You must have at least 100GB of available storage to install EOSIO."
		echo "exiting now"
		exit 1
	fi
	
	printf "\n\tChecking Yum installation\n"
	
	YUM=$( which yum 2>/dev/null )
	if [ $? -ne 0 ]; then
		printf "\n\tYum must be installed to compile EOS.IO.\n"
		printf "\n\tExiting now.\n"
		exit 0
	fi
	
	printf "\tYum installation found at ${YUM}.\n"
	printf "\tUpdating YUM.\n"
	UPDATE=$( sudo yum -y update )
	
	if [ $? -ne 0 ]; then
		printf "\n\tYUM update failed.\n"
		printf "\n\tExiting now.\n"
		exit 1
	fi
	
	printf "\t${UPDATE}\n"
# 	DEP_ARRAY=(clang-4.0 lldb-4.0 libclang-4.0-dev cmake make libbz2-dev libssl-dev libgmp3-dev autotools-dev build-essential libicu-dev python-dev autoconf libtool)
	DEP_ARRAY=( git gcc.x86_64 gcc-c++.x86_64 autoconf automake libtool make cmake.x86_64 bzip2 bzip2-devel.x86_64 openssl-devel.x86_64 gmp.x86_64 gmp-devel.x86_64 libstdc++-devel.x86_64 python3-devel.x86_64 libedit.x86_64 ncurses-devel.x86_64 swig.x86_64 )
	DCOUNT=0
	COUNT=1
	DISPLAY=""
	DEP=""

	printf "\n\tChecking YUM for installed dependencies.\n\n"

	for (( i=0; i<${#DEP_ARRAY[@]}; i++ ));
	do
		pkg=$( sudo $YUM info ${DEP_ARRAY[$i]} 2>/dev/null | grep Repo | tr -s ' ' | cut -d: -f2 | sed 's/ //g' )

		if [ "$pkg" != "@System" ]; then
			DEP=$DEP" ${DEP_ARRAY[$i]} "
			DISPLAY="${DISPLAY}${COUNT}. ${DEP_ARRAY[$i]}\n\t"
			printf "\tPackage ${DEP_ARRAY[$i]} ${bldred} NOT ${txtrst} found.\n"
			let COUNT++
			let DCOUNT++
		else
			printf "\tPackage ${DEP_ARRAY[$i]} found.\n"
			continue
		fi
	done		

	if [ ${DCOUNT} -ne 0 ]; then
		printf "\n\tThe following dependencies are required to install EOSIO.\n"
		printf "\n\t$DISPLAY\n\n"
		printf "\tDo you wish to install these dependencies?\n"
		select yn in "Yes" "No"; do
			case $yn in
				[Yy]* ) 
					printf "\n\n\tInstalling dependencies\n\n"
					sudo yum -y install ${DEP}
					if [ $? -ne 0 ]; then
						printf "\n\tYUM dependency installation failed.\n"
						printf "\n\tExiting now.\n"
						exit 1
					else
						printf "\n\tYUM dependencies installed successfully.\n"
					fi
				break;;
				[Nn]* ) echo "User aborting installation of required dependencies, Exiting now."; exit;;
				* ) echo "Please type 1 for yes or 2 for no.";;
			esac
		done
	else 
		printf "\n\tNo required YUM dependencies to install.\n"
	fi

	printf "\n\tChecking for boost libraries\n"
	if [ ! -d ${HOME}/opt/boost_1_66_0 ]; then
		# install boost
		printf "\tInstalling boost libraries\n"
		cd ${TEMP_DIR}
		curl -L https://dl.bintray.com/boostorg/release/1.66.0/source/boost_1_66_0.tar.bz2 > boost_1.66.0.tar.bz2
		tar xf boost_1.66.0.tar.bz2
		cd boost_1_66_0/
		./bootstrap.sh "--prefix=$BOOST_ROOT"
		./b2 install
		rm -rf ${TEMP_DIR}/boost_1_66_0/
		rm -f  ${TEMP_DIR}/boost_1.66.0.tar.bz2
	else
		printf "\tBoost 1.66 found at ${HOME}/opt/boost_1_66_0\n"
	fi

	printf "\n\tChecking for secp256k1-zkp\n"
    # install secp256k1-zkp (Cryptonomex branch)
    if [ ! -e /usr/local/lib/libsecp256k1.a ]; then
		printf "\tInstalling secp256k1-zkp (Cryptonomex branch)\n"
		cd ${TEMP_DIR}
		git clone https://github.com/cryptonomex/secp256k1-zkp.git
		cd secp256k1-zkp
		./autogen.sh
		if [ $? -ne 0 ]; then
			printf "\tError running autogen for secp256k1-zkp.\n"
			printf "\tExiting now.\n\n"
			exit;
		fi
		./configure
		make
		if [ $? -ne 0 ]; then
			printf "\tError compiling secp256k1-zkp.\n"
			printf "\tExiting now.\n\n"
			exit;
		fi
		sudo make install
		rm -rf cd ${TEMP_DIR}/secp256k1-zkp
	else
		printf "\tsecp256k1 found\n"
	fi
	
	printf "\n\tChecking for binaryen\n"
	if [ ! -d ${HOME}/opt/binaryen ]; then
		# Install binaryen v1.37.14:
		printf "\tInstalling binaryen v1.37.14:\n"
		cd ${TEMP_DIR}
		git clone https://github.com/WebAssembly/binaryen
		cd binaryen
		git checkout tags/1.37.14
		cmake . && make
		if [ $? -ne 0 ]; then
			printf "\tError compiling binaryen.\n"
			printf "\tExiting now.\n\n"
			exit;
		fi
		mkdir -p ${HOME}/opt/binaryen/ 2>/dev/null
		mv ${TEMP_DIR}/binaryen/{bin,src,lib} ${HOME}/opt/binaryen/
		rm -rf ${TEMP_DIR}/binaryen
	else
		printf "\tBinaryen found at ${HOME}/opt/binaryen\n"
	fi
	
	printf "\n\tChecking for LLVM with WASM support.\n"
	if [ ! -d ${HOME}/opt/wasm/bin ]; then
		# Build LLVM and clang with EXPERIMENTAL WASM support:
		printf "\tInstalling LLVM & WASM\n"
		cd ${TEMP_DIR}
		mkdir llvm-compiler  2>/dev/null
		cd llvm-compiler
		git clone --depth 1 --single-branch --branch release_40 https://github.com/llvm-mirror/llvm.git
		cd llvm/tools
		git clone --depth 1 --single-branch --branch release_40 https://github.com/llvm-mirror/clang.git
		cd ..
		mkdir build
		cd build
		cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX=${HOME}/opt/wasm -DLLVM_ENABLE_RTTI=1 -DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD=WebAssembly -DCMAKE_BUILD_TYPE=Release ../
		if [ $? -ne 0 ]; then
			printf "\tError compiling LLVM and clang with EXPERIMENTAL WASM support.\n"
			printf "\tExiting now.\n\n"
			exit;
		fi
		make -j$(nproc)
		if [ $? -ne 0 ]; then
			printf "\tError compiling LLVM and clang with EXPERIMENTAL WASM support.\n"
			printf "\tExiting now.\n\n"
			exit;
		fi
		make install
		rm -rf build
	else
		printf "\tWASM found at ${HOME}/opt/wasm\n"
	fi
	
	printf "\n\tChecking for LLVM with RTTI support.\n"
	if [ ! ${HOME}/opt/llvm/bin ]; then
		if [ ! -d ${TEMP_DIR}/llvm-compiler/llvm ]; then
			cd ${TEMP_DIR}
			mkdir llvm-compiler  2>/dev/null
			cd llvm-compiler
			git clone --depth 1 --single-branch --branch release_40 https://github.com/llvm-mirror/llvm.git
			cd llvm/tools
			git clone --depth 1 --single-branch --branch release_40 https://github.com/llvm-mirror/clang.git
		fi
		cd ${TEMP_DIR}/llvm-compiler/llvm
		mkdir build
		cd build
		cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX=${HOME}/opt/llvm -DCMAKE_BUILD_TYPE=release -DLLVM_ENABLE_RTTI=1 ../
		if [ $? -ne 0 ]; then
			printf "\tError compiling LLVM and clang with RTTI support.\n"
			printf "\tExiting now.\n\n"
			exit;
		fi
		make -j$(nproc)
		if [ $? -ne 0 ]; then
			printf "\tError compiling LLVM and clang with RTTI support.\n"
			printf "\tExiting now.\n\n"
			exit;
		fi
		make install
	fi

	rm -rf ${TEMP_DIR}/llvm-compiler 2>/dev/null