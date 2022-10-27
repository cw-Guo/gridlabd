#!/bin/bash

# check for Rosetta Homebrew

    if test -e /usr/local/Cellar; then 
        echo "ERROR: Use of Rosetta Homebrew creates package conflicts with arm64-native gridlabd installation in Darwin systems."
        echo "Please install in a system without Rosetta Homebrew, or you can attempt manual installation."
        exit 1
    fi

#!/bin/bash

# Set version and paths, using these vars will make future maintenance much better. #Automation
    VERSION=${VERSION:-`build-aux/version.sh --name`}
    VAR="/usr/local/opt/gridlabd"
    VERSION_DIR=$VAR/$VERSION
    PYTHON_DIR=Python.framework/Versions/Current
    PYTHON_VER=3.9.13
    PY_EXE=3.9

export PATH=$VERSION_DIR/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

# Check M1 Homebrew ownership
    if [ -e /opt/homebrew ] ; then
        sudo chown -R ${USER:-root} /opt/homebrew
    fi

# Check if python version currently in Applications and update owner
    if [ -e /Applications/"Python $PY_EXE" ] ; then
        sudo chown -R ${USER:-root} /Applications/"Python $PY_EXE"
    fi

brew update || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew doctor

# checking for necessary directories

    if test ! -e /usr/local/bin; then 
        cd /usr/local
        sudo mkdir bin
    fi

    if test ! -e /usr/local/lib; then 
        cd /usr/local
        sudo mkdir lib
    fi

    if test ! -e /usr/local/etc; then 
        cd /usr/local
        sudo mkdir etc
    fi


# install homebrew instance for gridlabd
    brew update
    if test ! -e /opt/homebrew; then 
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    export PATH=/opt/homebrew/bin:/opt/homebrew/sbin:$PATH
    brew update-reset
    brew doctor

# adding necessary paths to user bash and zsh terminals
# apparently, which profile or rc file is used varies wildly across Macs. RIP me. Add to all. =')
if ! grep -q "$VERSION_DIR/bin" "$HOME/.zshrc"; then
    touch "$HOME/.zshrc"
    echo "export PATH=$VERSION_DIR/bin:/opt/homebrew/bin:/opt/homebrew/sbin:\$PATH" >> $HOME/.zshrc
    echo "export DYLD_LIBRARY_PATH=$VERSION_DIR/lib:\$DYLD_LIBRARY_PATH" >> $HOME/.zshrc
    echo "export eval "$(/opt/homebrew/bin/brew shellenv)"" >> $HOME/.zshrc
fi

if ! grep -q "$VERSION_DIR/bin" "$HOME/.zsh_profile"; then
    touch "$HOME/.zsh_profile"
    echo "export PATH=$VERSION_DIR/bin:/opt/homebrew/bin:/opt/homebrew/sbin:\$PATH" >> $HOME/.zsh_profile
    echo "export DYLD_LIBRARY_PATH=$VERSION_DIR/lib:\$DYLD_LIBRARY_PATH" >> $HOME/.zsh_profile
    echo "export eval "$(/opt/homebrew/bin/brew shellenv)"" >> $HOME/.zsh_profile
fi

if ! grep -q "$VERSION_DIR/bin" "$HOME/.bash_profile"; then
    touch "$HOME/.bash_profile"
    echo "export PATH=$VERSION_DIR/bin:/opt/homebrew/bin:/opt/homebrew/sbin:\$PATH" >> $HOME/.bash_profile
    echo "export DYLD_LIBRARY_PATH=$VERSION_DIR/lib:/opt/homebrew/lib:\$DYLD_LIBRARY_PATH" >> $HOME/.bash_profile
    echo "export LD_LIBRARY_PATH=$VERSION_DIR/lib:/opt/homebrew/lib:\$LD_LIBRARY_PATH" >> $HOME/.bash_profile
    echo "export LIBRARY_PATH=$VERSION_DIR/lib:/opt/homebrew/lib:\$LIBRARY_PATH" >> $HOME/.bash_profile
    echo "export eval "$(/opt/homebrew/bin/brew shellenv)"" >> $HOME/.bash_profile
fi

if ! grep -q "$VERSION_DIR/lib" "$HOME/.bashrc"; then
    touch "$HOME/.bashrc"
    echo "export PATH=$VERSION_DIR/bin:/opt/homebrew/bin:/opt/homebrew/sbin:\$PATH" >> $HOME/.bashrc
    echo "export DYLD_LIBRARY_PATH=$VERSION_DIR/lib:/opt/homebrew/lib:\$DYLD_LIBRARY_PATH" >> $HOME/.bashrc
    echo "export LD_LIBRARY_PATH=$VERSION_DIR/lib:/opt/homebrew/lib:\$LD_LIBRARY_PATH" >> $HOME/.bashrc
    echo "export LIBRARY_PATH=$VERSION_DIR/lib:/opt/homebrew/lib:\$LIBRARY_PATH" >> $HOME/.bashrc
    echo "export eval "$(/opt/homebrew/bin/brew shellenv)"" >> $HOME/.bashrc
fi

export DYLD_LIBRARY_PATH=$VERSION_DIR/lib:/opt/homebrew/lib:$DYLD_LIBRARY_PATH
export DYLD_LIBRARY_PATH=$VERSION_DIR/lib:/opt/homebrew/lib:$DYLD_LIBRARY_PATH
export LD_LIBRARY_PATH=$VERSION_DIR/lib:/opt/homebrew/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$VERSION_DIR/lib:/opt/homebrew/lib:$LD_LIBRARY_PATH
export LIBRARY_PATH=$VERSION_DIR/lib:/opt/homebrew/lib:$LIBRARY_PATH
export LIBRARY_PATH=$VERSION_DIR/lib:/opt/homebrew/lib:$LIBRARY_PATH

# build tools

    brew install autoconf automake libtool gnu-sed gawk git
    brew install libffi zlib
    brew install pkg-config xz gdbm tcl-tk
    xcode-select --install

# Update symlinks in /usr/local/bin
    [ ! -e /usr/local/bin/sed ] && sudo ln -sf /opt/homebrew/bin/gsed /usr/local/bin/sed
    [ ! -e /usr/local/bin/libtoolize ] && sudo ln -sf /opt/homebrew/bin/glibtoolize /usr/local/bin/libtoolize
    [ ! -e /usr/local/bin/libtool ] && sudo ln -sf /opt/homebrew/bin/glibtool /usr/local/bin/libtool


# mdbtools
    brew install mdbtools

# The original scikit-learn at 0.24.2 CANNOT install on the m1 mac. Period. Use 1.1.1 now. Make sure requirements.txt has the change.
# Reason being, is that it requires a version of NumPy that is incompatible with the m1 mac.
# updated in requirements.txt. Same goes for scipy 1.6.2. Use 1.8.1.
    brew install gdal

# docs generators
    brew install mono
    brew install naturaldocs
    sudo ln -sf /opt/homebrew/bin/naturaldocs /usr/local/bin/natural_docs

    brew install doxygen

# influxdb
    brew install influxdb
    brew services start influxdb

# subversion cli
    brew install svn

# libgeos
    brew install geos
    cp /opt/homebrew/lib/libgeos* $VERSION_DIR/lib

    if test ! -e /usr/local/lib; then
        cd /usr/local
        sudo mkdir lib
    fi

    ln -sf $VERSION_DIR/gridlabd/lib/libgeos* /usr/local/lib 

# mysql connector
#    brew install mysql
#    brew install mysql-client

sudo ln -s /opt/homebrew/bin/* /usr/local/bin
sudo ln -s /opt/homebrew/etc/* /usr/local/etc

cd /usr/local/bin
sudo rm -rf brew
