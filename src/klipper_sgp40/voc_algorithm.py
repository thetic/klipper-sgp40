# SPDX-FileCopyrightText: Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com)
#
# SPDX-License-Identifier: MIT
# Author(s): yangfeng

from math import exp, sqrt

_INITIAL_BLACKOUT_SEC = 45.0
_VOC_INDEX_GAIN = 230.0
_SRAW_MINIMUM = 20000
_SRAW_STD_INITIAL = 50.0
_SRAW_STD_BONUS = 220.0
_TAU_MEAN_VARIANCE_HOURS = 12.0
_TAU_INITIAL_MEAN = 20
_INITI_DURATION_MEAN = 2700.0
_INITI_TRANSITION_MEAN = 0.01
_TAU_INITIAL_VARIANCE = 2500
_INITI_DURATION_VARIANCE = 5220.0
_INITI_TRANSITION_VARIANCE = 0.01
_GATING_THRESHOLD = 340.0
_GATING_THRESHOLD_INITIAL = 510.0
_GATING_THRESHOLD_TRANSITION = 0.09
_GATING_MAX_DURATION_MINUTES = 180.0
_GATING_MAX_RATIO = 0.3
_SIGMOID_L = 500.0
_SIGMOID_K = -0.0065
_SIGMOID_X0 = 213.0
_VOC_INDEX_OFFSET_DEFAULT = 100.0
_LP_TAU_FAST = 20.0
_LP_TAU_SLOW = 500.0
_LP_ALPHA = -0.2
_PERSISTENCE_UPTIME_GAMMA = 10800.0
_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING = 64.0
_MEAN_VARIANCE_ESTIMATOR__FIX16_MAX = 32767


class Params:
    """Class for voc index algorithm"""

    def __init__(self):
        self.voc_index_offset = _VOC_INDEX_OFFSET_DEFAULT
        self.tau_mean_variance_hours = _TAU_MEAN_VARIANCE_HOURS
        self.gating_max_duration_minutes = _GATING_MAX_DURATION_MINUTES
        self.sraw_std_initial = _SRAW_STD_INITIAL
        self.uptime = 0.0
        self.sraw = 0.0
        self.voc_index = 0.0
        self.mean_variance_estimator_gating_max_duration_minutes = 0.0
        self.mean_variance_estimator_initialized = False
        self.mean_variance_estimator_mean = 0.0
        self.mean_variance_estimator_sraw_offset = 0.0
        self.mean_variance_estimator_std = 0.0
        self.mean_variance_estimator_gamma = 0.0
        self.mean_variance_estimator_gamma_initial_mean = 0.0
        self.mean_variance_estimator_gamma_initial_variance = 0.0
        self.mean_variance_estimator_gamma_mean = 0.0
        self.mean_variance_estimator__gamma_variance = 0.0
        self.mean_variance_estimator_uptime_gamma = 0.0
        self.mean_variance_estimator_uptime_gating = 0.0
        self.mean_variance_estimator_gating_duration_minutes = 0.0
        self.mean_variance_estimator_sigmoid_l = 0.0
        self.mean_variance_estimator_sigmoid_k = 0.0
        self.mean_variance_estimator_sigmoid_x0 = 0.0
        self.mox_model_sraw_mean = 0.0
        self.mox_model_sraw_std = 0.0
        self.sigmoid_scaled_offset = 0.0
        self.adaptive_lowpass_a1 = 0.0
        self.adaptive_lowpass_a2 = 0.0
        self.adaptive_lowpass_initialized = False
        self.adaptive_lowpass_x1 = 0.0
        self.adaptive_lowpass_x2 = 0.0
        self.adaptive_lowpass_x3 = 0.0


class VocAlgorithm:
    SAMPLE_PEROID_SEC = 1.0

    def __init__(self):
        self._params = Params()
        self.calibrating = True
        self._init_instances()

    def _init_instances(self):
        self._mean_variance_estimator_init()
        self._mean_variance_estimator_set_parameters(
            _SRAW_STD_INITIAL,
            self._params.tau_mean_variance_hours,
            self._params.gating_max_duration_minutes,
        )
        self._mox_model_init()
        self._mox_model_set_parameters(
            self._mean_variance_estimator_get_std(),
            self._mean_variance_estimator_get_mean(),
        )
        self._sigmoid_scaled_init()
        self._sigmoid_scaled_set_parameters(self._params.voc_index_offset)
        self._adaptive_lowpass_init()
        self._adaptive_lowpass_set_parameters()

    def get_states(self):
        state0 = self._mean_variance_estimator_get_mean()
        state1 = self._mean_variance_estimator_get_std()
        return state0, state1

    def set_states(self, state0, state1):
        self._mean_variance_estimator_set_states(
            state0,
            state1,
            _PERSISTENCE_UPTIME_GAMMA,
        )
        self._params.sraw = state0

    def set_tuning_parameters(
        self,
        voc_index_offset,
        learning_time_hours,
        gating_max_duration_minutes,
        std_initial,
    ):
        self._params.voc_index_offset = float(voc_index_offset)
        self._params.tau_mean_variance_hours = float(learning_time_hours)
        self._params.gating_max_duration_minutes = float(gating_max_duration_minutes)
        self._params.sraw_std_initial = float(std_initial)
        self._init_instances()

    def process(self, sraw):
        if self._params.uptime <= _INITIAL_BLACKOUT_SEC:
            self._params.uptime += self.SAMPLE_PEROID_SEC
        else:
            if (sraw > 0) and (sraw < 65000):
                if sraw < _SRAW_MINIMUM + 1:
                    sraw = _SRAW_MINIMUM + 1
                elif sraw > (_SRAW_MINIMUM + 32767):
                    sraw = _SRAW_MINIMUM + 32767
                self._params.sraw = float(sraw - _SRAW_MINIMUM)
            self._params.voc_index = self._mox_model_process(self._params.sraw)
            self._params.voc_index = self._sigmoid_scaled_process(
                self._params.voc_index
            )
            self._params.voc_index = self._adaptive_lowpass_process(
                self._params.voc_index
            )
            if self._params.voc_index < 0.5:
                self._params.voc_index = 0.5
            if self._params.sraw > 0.0:
                self._mean_variance_estimator_process(
                    self._params.sraw, self._params.voc_index
                )
                self._mox_model_set_parameters(
                    self._mean_variance_estimator_get_std(),
                    self._mean_variance_estimator_get_mean(),
                )
        voc_index = round(self._params.voc_index)
        return voc_index

    def _mean_variance_estimator_init(self):
        self._mean_variance_estimator_set_parameters(0.0, 0.0, 0.0)
        self._mean_variance_estimator_init_instances()

    def _mean_variance_estimator_init_instances(self):
        self._mean_variance_estimator_sigmoid_init()

    def _mean_variance_estimator_set_parameters(
        self, std_initial, tau_mean_variance_hours, gating_max_duration_minutes
    ):
        self._params.mean_variance_estimator_gating_max_duration_minutes = (
            gating_max_duration_minutes
        )
        self._params.mean_variance_estimator_initialized = False
        self._params.mean_variance_estimator_mean = 0.0
        self._params.mean_variance_estimator_sraw_offset = 0.0
        self._params.mean_variance_estimator_std = std_initial
        self._params.mean_variance_estimator_gamma = (
            _MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING * (self.SAMPLE_PEROID_SEC / 3600.0)
        ) / (tau_mean_variance_hours + (self.SAMPLE_PEROID_SEC / 3600.0))
        self._params.mean_variance_estimator_gamma_initial_mean = (
            _MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING * self.SAMPLE_PEROID_SEC
        ) / (_TAU_INITIAL_MEAN + self.SAMPLE_PEROID_SEC)
        self._params.mean_variance_estimator_gamma_initial_variance = (
            _MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING * self.SAMPLE_PEROID_SEC
        ) / (_TAU_INITIAL_VARIANCE + self.SAMPLE_PEROID_SEC)
        self._params.mean_variance_estimator_gamma_mean = 0.0
        self._params.mean_variance_estimator__gamma_variance = 0.0
        self._params.mean_variance_estimator_uptime_gamma = 0.0
        self._params.mean_variance_estimator_uptime_gating = 0.0
        self._params.mean_variance_estimator_gating_duration_minutes = 0.0

    def _mean_variance_estimator_set_states(self, mean, std, uptime_gamma):
        self._params.mean_variance_estimator_mean = mean
        self._params.mean_variance_estimator_std = std
        self._params.mean_variance_estimator_uptime_gamma = uptime_gamma
        self._params.mean_variance_estimator_initialized = True

    def _mean_variance_estimator_get_std(self):
        return self._params.mean_variance_estimator_std

    def _mean_variance_estimator_get_mean(self):
        return (
            self._params.mean_variance_estimator_mean
            + self._params.mean_variance_estimator_sraw_offset
        )

    def _mean_variance_estimator_calculate_gamma(self, voc_index_from_prior):
        uptime_limit = _MEAN_VARIANCE_ESTIMATOR__FIX16_MAX - self.SAMPLE_PEROID_SEC
        if self._params.mean_variance_estimator_uptime_gamma < uptime_limit:
            self._params.mean_variance_estimator_uptime_gamma = (
                self._params.mean_variance_estimator_uptime_gamma
                + self.SAMPLE_PEROID_SEC
            )

        if self._params.mean_variance_estimator_uptime_gating < uptime_limit:
            self._params.mean_variance_estimator_uptime_gating = (
                self._params.mean_variance_estimator_uptime_gating
                + self.SAMPLE_PEROID_SEC
            )

        self._mean_variance_estimator_sigmoid_set_parameters(
            1.0,
            _INITI_DURATION_MEAN,
            _INITI_TRANSITION_MEAN,
        )
        sigmoid_gamma_mean = self._mean_variance_estimator_sigmoid_process(
            self._params.mean_variance_estimator_uptime_gamma
        )
        gamma_mean = self._params.mean_variance_estimator_gamma + (
            (
                self._params.mean_variance_estimator_gamma_initial_mean
                - self._params.mean_variance_estimator_gamma
            )
            * sigmoid_gamma_mean
        )
        gating_threshold_mean = _GATING_THRESHOLD + (
            (_GATING_THRESHOLD_INITIAL - _GATING_THRESHOLD)
            * self._mean_variance_estimator_sigmoid_process(
                self._params.mean_variance_estimator_uptime_gating
            )
        )
        self._mean_variance_estimator_sigmoid_set_parameters(
            1.0,
            gating_threshold_mean,
            _GATING_THRESHOLD_TRANSITION,
        )

        sigmoid_gating_mean = self._mean_variance_estimator_sigmoid_process(
            voc_index_from_prior
        )
        self._params.mean_variance_estimator_gamma_mean = (
            sigmoid_gating_mean * gamma_mean
        )

        self._mean_variance_estimator_sigmoid_set_parameters(
            1.0,
            _INITI_DURATION_VARIANCE,
            _INITI_TRANSITION_VARIANCE,
        )

        sigmoid_gamma_variance = self._mean_variance_estimator_sigmoid_process(
            self._params.mean_variance_estimator_uptime_gamma
        )

        gamma_variance = self._params.mean_variance_estimator_gamma + (
            (
                self._params.mean_variance_estimator_gamma_initial_variance
                - self._params.mean_variance_estimator_gamma
            )
            * (sigmoid_gamma_variance - sigmoid_gamma_mean)
        )

        gating_threshold_variance = _GATING_THRESHOLD + (
            (_GATING_THRESHOLD_INITIAL - _GATING_THRESHOLD)
            * self._mean_variance_estimator_sigmoid_process(
                self._params.mean_variance_estimator_uptime_gating
            )
        )

        self._mean_variance_estimator_sigmoid_set_parameters(
            1.0,
            gating_threshold_variance,
            _GATING_THRESHOLD_TRANSITION,
        )

        sigmoid_gating_variance = self._mean_variance_estimator_sigmoid_process(
            voc_index_from_prior
        )

        self._params.mean_variance_estimator__gamma_variance = (
            sigmoid_gating_variance * gamma_variance
        )

        self._params.mean_variance_estimator_gating_duration_minutes = (
            self._params.mean_variance_estimator_gating_duration_minutes
            + (
                (self.SAMPLE_PEROID_SEC / 60.0)
                * (
                    ((1.0 - sigmoid_gating_mean) * (1.0 + _GATING_MAX_RATIO))
                    - _GATING_MAX_RATIO
                )
            )
        )

        if self._params.mean_variance_estimator_gating_duration_minutes < 0.0:
            self._params.mean_variance_estimator_gating_duration_minutes = 0.0

        if (
            self._params.mean_variance_estimator_gating_duration_minutes
            > self._params.mean_variance_estimator_gating_max_duration_minutes
        ):
            self._params.mean_variance_estimator_uptime_gating = 0.0

    def _mean_variance_estimator_process(self, sraw, voc_index_from_prior):
        if not self._params.mean_variance_estimator_initialized:
            self._params.mean_variance_estimator_initialized = True
            self._params.mean_variance_estimator_sraw_offset = sraw
            self._params.mean_variance_estimator_mean = 0.0
        else:
            if (self._params.mean_variance_estimator_mean >= 100.0) or (
                self._params.mean_variance_estimator_mean <= -100.0
            ):
                self._params.mean_variance_estimator_sraw_offset = (
                    self._params.mean_variance_estimator_sraw_offset
                    + self._params.mean_variance_estimator_mean
                )
                self._params.mean_variance_estimator_mean = 0.0

            sraw = sraw - self._params.mean_variance_estimator_sraw_offset
            self._mean_variance_estimator_calculate_gamma(voc_index_from_prior)
            delta_sgp = (sraw - self._params.mean_variance_estimator_mean) / (
                _MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING
            )
            if delta_sgp < 0.0:
                c = self._params.mean_variance_estimator_std - delta_sgp
            else:
                c = self._params.mean_variance_estimator_std + delta_sgp
            additional_scaling = 1.0
            if c > 1440.0:
                additional_scaling = 4.0
            self._params.mean_variance_estimator_std = (
                sqrt(
                    additional_scaling
                    * (
                        _MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING
                        - self._params.mean_variance_estimator__gamma_variance
                    )
                )
            ) * sqrt(
                (
                    self._params.mean_variance_estimator_std
                    * (
                        self._params.mean_variance_estimator_std
                        / (_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING * additional_scaling)
                    )
                )
                + (
                    (
                        (
                            self._params.mean_variance_estimator__gamma_variance
                            * delta_sgp
                        )
                        / additional_scaling
                    )
                    * delta_sgp
                )
            )
            self._params.mean_variance_estimator_mean = (
                self._params.mean_variance_estimator_mean
                + (self._params.mean_variance_estimator_gamma_mean * delta_sgp)
            )

    def _mean_variance_estimator_sigmoid_init(self):
        self._mean_variance_estimator_sigmoid_set_parameters(0.0, 0.0, 0.0)

    def _mean_variance_estimator_sigmoid_set_parameters(
        self, l_param, x0_param, k_param
    ):
        self._params.mean_variance_estimator_sigmoid_l = l_param
        self._params.mean_variance_estimator_sigmoid_k = k_param
        self._params.mean_variance_estimator_sigmoid_x0 = x0_param

    def _mean_variance_estimator_sigmoid_process(self, sample):
        if not self.calibrating:
            # Hack stolen from sanaa to disable all gating and freeze the MVE
            return 0.0

        x = self._params.mean_variance_estimator_sigmoid_k * (
            sample - self._params.mean_variance_estimator_sigmoid_x0
        )
        if x < -50.0:
            return self._params.mean_variance_estimator_sigmoid_l
        elif x > 50.0:
            return 0.0
        else:
            return self._params.mean_variance_estimator_sigmoid_l / (1.0 + exp(x))

    def _mox_model_init(self):
        self._mox_model_set_parameters(1.0, 0.0)

    def _mox_model_set_parameters(self, std, mean):
        self._params.mox_model_sraw_std = std
        self._params.mox_model_sraw_mean = mean

    def _mox_model_process(self, sraw):
        return (
            (sraw - self._params.mox_model_sraw_mean)
            / -(self._params.mox_model_sraw_std + _SRAW_STD_BONUS)
        ) * _VOC_INDEX_GAIN

    def _sigmoid_scaled_init(self):
        self._sigmoid_scaled_set_parameters(0.0)

    def _sigmoid_scaled_set_parameters(self, offset):
        self._params.sigmoid_scaled_offset = offset

    def _sigmoid_scaled_process(self, sample):
        x = _SIGMOID_K * (sample - _SIGMOID_X0)
        if x < -50.0:
            return _SIGMOID_L
        elif x > 50.0:
            return 0.0
        else:
            if sample >= 0.0:
                shift = (_SIGMOID_L - (5.0 * self._params.sigmoid_scaled_offset)) / 4.0
                return ((_SIGMOID_L + shift) / (1.0 + exp(x))) - shift
            else:
                return (
                    self._params.sigmoid_scaled_offset / _VOC_INDEX_OFFSET_DEFAULT
                ) * (_SIGMOID_L / (1.0 + exp(x)))

    def _adaptive_lowpass_init(self):
        self._adaptive_lowpass_set_parameters()

    def _adaptive_lowpass_set_parameters(self):
        self._params.adaptive_lowpass_a1 = self.SAMPLE_PEROID_SEC / (
            _LP_TAU_FAST + self.SAMPLE_PEROID_SEC
        )
        self._params.adaptive_lowpass_a2 = self.SAMPLE_PEROID_SEC / (
            _LP_TAU_SLOW + self.SAMPLE_PEROID_SEC
        )
        self._params.adaptive_lowpass_initialized = False

    def _adaptive_lowpass_process(self, sample):
        if not self._params.adaptive_lowpass_initialized:
            self._params.adaptive_lowpass_x1 = sample
            self._params.adaptive_lowpass_x2 = sample
            self._params.adaptive_lowpass_x3 = sample
            self._params.adaptive_lowpass_initialized = True
        self._params.adaptive_lowpass_x1 = (
            (1.0 - self._params.adaptive_lowpass_a1) * self._params.adaptive_lowpass_x1
        ) + (self._params.adaptive_lowpass_a1 * sample)

        self._params.adaptive_lowpass_x2 = (
            (1.0 - self._params.adaptive_lowpass_a2) * self._params.adaptive_lowpass_x2
        ) + (self._params.adaptive_lowpass_a2 * sample)

        abs_delta = self._params.adaptive_lowpass_x1 - self._params.adaptive_lowpass_x2

        if abs_delta < 0.0:
            abs_delta = -abs_delta
        f1 = exp(_LP_ALPHA * abs_delta)
        tau_a = ((_LP_TAU_SLOW - _LP_TAU_FAST) * f1) + (_LP_TAU_FAST)
        a3 = self.SAMPLE_PEROID_SEC / (self.SAMPLE_PEROID_SEC + tau_a)
        self._params.adaptive_lowpass_x3 = (
            (1.0 - a3) * self._params.adaptive_lowpass_x3
        ) + (a3 * sample)
        return self._params.adaptive_lowpass_x3
