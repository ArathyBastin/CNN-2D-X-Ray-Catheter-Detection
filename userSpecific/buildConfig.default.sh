_OPTIONS= 

_OPTIONS="$_OPTIONS -DMAKE_PYTHON_WRAPPER=ON -DBOOST_ROOT=$_BOOST_SRC_DIR -D_BOOST_PYTHON_LIB=$_BOOST_PYTHON_LIB -D_BOOST_NUMPY_LIB=$_BOOST_NUMPY_LIB"

# _OPTIONS="$_OPTIONS -DPYTHON_DEBUG_OUTPUT=ON"
_OPTIONS="$_OPTIONS -DPYTHON_DEBUG_OUTPUT=OFF"