# Copyright 2016 the GPflow authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.from __future__ import print_function

import GPflow
import numpy as np
import unittest
import tensorflow as tf


class TestEquivalence(unittest.TestCase):
    """
    With a Gaussian likelihood, and inducing points (where appropriate)
    positioned at the data, many of the GPflow methods are equivalent (perhaps
    subject to some optimization).

    Here, we make 5 models that should be the same, and make sure some
    similarites hold. The models are:

    1) GP Regression
    2) Variational GP (with the likelihood set to Gaussian)
    3) Sparse variational GP (likelihood is Gaussian, inducing points
       at the data)
    4) Sparse variational GP (as above, but with the whitening rotation
       of the inducing variables)
    5) Sparse variational GP Regression (as above, but there the inducing
       variables are 'collapsed' out, as in Titsias 2009)
    """
    def setUp(self):
        tf.reset_default_graph()
        rng = np.random.RandomState(0)
        X = rng.rand(20, 1)*10
        Y = np.sin(X) + 0.9 * np.cos(X*1.6) + rng.randn(*X.shape) * 0.8
        Y = np.tile(Y, 2) # two identical columns
        self.Xtest = rng.rand(10, 1)*10

        m1 = GPflow.gpr.GPR(X, Y, kern=GPflow.kernels.RBF(1),
                            mean_function=GPflow.mean_functions.Constant())
        m2 = GPflow.vgp.VGP(X, Y, GPflow.kernels.RBF(1), likelihood=GPflow.likelihoods.Gaussian(),
                            mean_function=GPflow.mean_functions.Constant())
        m3 = GPflow.svgp.SVGP(X, Y, GPflow.kernels.RBF(1),
                              likelihood=GPflow.likelihoods.Gaussian(),
                              Z=X.copy(), q_diag=False,
                              mean_function=GPflow.mean_functions.Constant())
        m3.Z.fixed = True
        m4 = GPflow.svgp.SVGP(X, Y, GPflow.kernels.RBF(1),
                              likelihood=GPflow.likelihoods.Gaussian(),
                              Z=X.copy(), q_diag=False, whiten=True,
                              mean_function=GPflow.mean_functions.Constant())
        m4.Z.fixed = True
        m5 = GPflow.sgpr.SGPR(X, Y, GPflow.kernels.RBF(1),
                              Z=X.copy(),
                              mean_function=GPflow.mean_functions.Constant())

        m5.Z.fixed = True
        m6 = GPflow.sgpr.GPRFITC(X, Y, GPflow.kernels.RBF(1), Z=X.copy(),
                                 mean_function=GPflow.mean_functions.Constant())
        m6.Z.fixed = True
        self.models = [m1, m2, m3, m4, m5, m6]
        for m in self.models:
            m.optimize(disp=False, maxiter=300)
            print('.')  # stop travis timing out

    def test_all(self):
        likelihoods = np.array([-m._objective(m.get_free_state())[0].squeeze() for m in self.models])
        self.assertTrue(np.allclose(likelihoods, likelihoods[0], 1e-6))
        variances, lengthscales = [], []
        for m in self.models:
            if hasattr(m.kern, 'rbf'):
                variances.append(m.kern.rbf.variance.value)
                lengthscales.append(m.kern.rbf.lengthscales.value)
            else:
                variances.append(m.kern.variance.value)
                lengthscales.append(m.kern.lengthscales.value)
        variances, lengthscales = np.array(variances), np.array(lengthscales)
        self.assertTrue(np.allclose(variances, variances[0], 1e-5))
        self.assertTrue(np.allclose(lengthscales, lengthscales.mean(), 1e-4))
        mu0, var0 = self.models[0].predict_y(self.Xtest)
        for m in self.models[1:]:
            mu, var = m.predict_y(self.Xtest)
            self.assertTrue(np.allclose(mu, mu0, 1e-3))
            self.assertTrue(np.allclose(var, var0, 1e-4))


if __name__ == '__main__':
    unittest.main()
