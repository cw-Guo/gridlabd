#!/bin/bash

# Set version and paths, using these vars will make future maintenance much better. #Automation
    VERSION=${VERSION:-`build-aux/version.sh --name`}
    VAR="/usr/local/opt/gridlabd"
    VERSION_DIR=$VAR/$VERSION
    PYTHON_DIR=Python.framework/Versions/Current
    PYTHON_VER=3.9.13
    PY_EXE=3.9

export PATH=$VERSION_DIR/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

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

# adding necessary paths to user bash and zsh terminals
# apparently, which profile or rc file is used varies wildly across Macs. RIP me. Add to all. =')
if ! grep -q "$VERSION_DIR/bin" "$HOME/.zshrc"; then
    touch "$HOME/.zshrc"
    echo "export PATH=$VERSION_DIR/bin:\$PATH" >> $HOME/.zshrc
    echo "export DYLD_LIBRARY_PATH=$VERSION_DIR/lib:\$DYLD_LIBRARY_PATH" >> $HOME/.zshrc
fi

if ! grep -q "$VERSION_DIR/bin" "$HOME/.zsh_profile"; then
    touch "$HOME/.zsh_profile"
    echo "export PATH=$VERSION_DIR/bin:\$PATH" >> $HOME/.zsh_profile
    echo "export DYLD_LIBRARY_PATH=$VERSION_DIR/lib:\$DYLD_LIBRARY_PATH" >> $HOME/.zsh_profile
fi

if ! grep -q "$VERSION_DIR/bin" "$HOME/.bash_profile"; then
    touch "$HOME/.bash_profile"
    echo "export PATH=$VERSION_DIR/bin:\$PATH" >> $HOME/.bash_profile
    echo "export DYLD_LIBRARY_PATH=$VERSION_DIR/lib:\$DYLD_LIBRARY_PATH" >> $HOME/.bash_profile
    echo "export LD_LIBRARY_PATH=$VERSION_DIR/lib:\$LD_LIBRARY_PATH" >> $HOME/.bash_profile
    echo "export LIBRARY_PATH=$VERSION_DIR/lib:\$LIBRARY_PATH" >> $HOME/.bash_profile
fi

if ! grep -q "$VERSION_DIR/lib" "$HOME/.bashrc"; then
    touch "$HOME/.bashrc"
    echo "export PATH=$VERSION_DIR/bin:\$PATH" >> $HOME/.bashrc
    echo "export DYLD_LIBRARY_PATH=$VERSION_DIR/lib:\$DYLD_LIBRARY_PATH" >> $HOME/.bashrc
    echo "export LD_LIBRARY_PATH=$VERSION_DIR/lib:\$LD_LIBRARY_PATH" >> $HOME/.bashrc
    echo "export LIBRARY_PATH=$VERSION_DIR/lib:\$LIBRARY_PATH" >> $HOME/.bashrc
fi

export DYLD_LIBRARY_PATH=$VERSION_DIR/lib:$DYLD_LIBRARY_PATH
export DYLD_LIBRARY_PATH=$VERSION_DIR/lib:$DYLD_LIBRARY_PATH
export LD_LIBRARY_PATH=$VERSION_DIR/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$VERSION_DIR/lib:$LD_LIBRARY_PATH
export LIBRARY_PATH=$VERSION_DIR/lib:$LIBRARY_PATH
export LIBRARY_PATH=$VERSION_DIR/lib:$LIBRARY_PATH

# build tools

    brew install autoconf automake libtool gnu-sed gawk git
    brew install libffi zlib
    brew install pkg-config xz gdbm tcl-tk
    xcode-select --install

# Update symlinks in /usr/local/bin
    [ ! -e /usr/local/bin/sed ] && sudo ln -sf /usr/local/bin/gsed /usr/local/bin/sed
    [ ! -e /usr/local/bin/libtoolize ] && sudo ln -sf /usr/local/bin/glibtoolize /usr/local/bin/libtoolize
    [ ! -e /usr/local/bin/libtool ] && sudo ln -sf /usr/local/bin/glibtool /usr/local/bin/libtool


brew install gdal

# docs generators
    brew install mono
    brew install naturaldocs
    sudo ln -sf /usr/local/bin/naturaldocs /usr/local/bin/natural_docs

    brew install doxygen

# influxdb
    brew install influxdb
    brew services start influxdb

# subversion cli
    brew install svn

# libgeos
    brew install geos
    cp /usr/local/opt/geos/lib/libgeos* $VERSION_DIR/lib

    if test ! -e /usr/local/lib; then
        cd /usr/local
        sudo mkdir lib
    fi
