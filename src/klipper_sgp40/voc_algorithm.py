# SPDX-FileCopyrightText: Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com)
#
# SPDX-License-Identifier: MIT
# Author(s): yangfeng

from math import exp, sqrt

_VOCALGORITHM_SAMPLING_INTERVAL = 1.0
_VOCALGORITHM_INITIAL_BLACKOUT = 45.0
_VOCALGORITHM_VOC_INDEX_GAIN = 230.0
_VOCALGORITHM_SRAW_STD_INITIAL = 50.0
_VOCALGORITHM_SRAW_STD_BONUS = 220.0
_VOCALGORITHM_TAU_MEAN_VARIANCE_HOURS = 12.0
_VOCALGORITHM_TAU_INITIAL_MEAN = 20
_VOCALGORITHM_INITI_DURATION_MEAN = 2700.0
_VOCALGORITHM_INITI_TRANSITION_MEAN = 0.01
_VOCALGORITHM_TAU_INITIAL_VARIANCE = 2500
_VOCALGORITHM_INITI_DURATION_VARIANCE = 5220.0
_VOCALGORITHM_INITI_TRANSITION_VARIANCE = 0.01
_VOCALGORITHM_GATING_THRESHOLD = 340.0
_VOCALGORITHM_GATING_THRESHOLD_INITIAL = 510.0
_VOCALGORITHM_GATING_THRESHOLD_TRANSITION = 0.09
_VOCALGORITHM_GATING_MAX_DURATION_MINUTES = 180.0
_VOCALGORITHM_GATING_MAX_RATIO = 0.3
_VOCALGORITHM_SIGMOID_L = 500.0
_VOCALGORITHM_SIGMOID_K = -0.0065
_VOCALGORITHM_SIGMOID_X0 = 213.0
_VOCALGORITHM_VOC_INDEX_OFFSET_DEFAULT = 100.0
_VOCALGORITHM_LP_TAU_FAST = 20.0
_VOCALGORITHM_LP_TAU_SLOW = 500.0
_VOCALGORITHM_LP_ALPHA = -0.2
_VOCALGORITHM_PERSISTENCE_UPTIME_GAMMA = 10800.0
_VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING = 64.0
_VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__FIX16_MAX = 32767


class DFRobot_vocalgorithmParams:
    """Class for voc index algorithm"""

    def __init__(self):
        self.mvoc_index_offset = 0.0
        self.mtau_mean_variance_hours = 0.0
        self.mgating_max_duration_minutes = 0.0
        self.msraw_std_initial = 0.0
        self.muptime = 0.0
        self.msraw = 0.0
        self.mvoc_index = 0.0
        self.m_mean_variance_estimator_gating_max_duration_minutes = 0.0
        self.m_mean_variance_estimator_initialized = False
        self.m_mean_variance_estimator_mean = 0.0
        self.m_mean_variance_estimator_sraw_offset = 0.0
        self.m_mean_variance_estimator_std = 0.0
        self.m_mean_variance_estimator_gamma = 0.0
        self.m_mean_variance_estimator_gamma_initial_mean = 0.0
        self.m_mean_variance_estimator_gamma_initial_variance = 0.0
        self.m_mean_variance_estimator_gamma_mean = 0.0
        self.m_mean_variance_estimator__gamma_variance = 0.0
        self.m_mean_variance_estimator_uptime_gamma = 0.0
        self.m_mean_variance_estimator_uptime_gating = 0.0
        self.m_mean_variance_estimator_gating_duration_minutes = 0.0
        self.m_mean_variance_estimator_sigmoid_l = 0.0
        self.m_mean_variance_estimator_sigmoid_k = 0.0
        self.m_mean_variance_estimator_sigmoid_x0 = 0.0
        self.m_mox_model_sraw_mean = 0.0
        self.m_mox_model_sraw_std = 0.0
        self.m_sigmoid_scaled_offset = 0.0
        self.m_adaptive_lowpass_a1 = 0.0
        self.m_adaptive_lowpass_a2 = 0.0
        self.m_adaptive_lowpass_initialized = False
        self.m_adaptive_lowpass_x1 = 0.0
        self.m_adaptive_lowpass_x2 = 0.0
        self.m_adaptive_lowpass_x3 = 0.0


class VocAlgorithm:
    def __init__(self):
        self.params = DFRobot_vocalgorithmParams()
        self.vocalgorithm_init()

    def vocalgorithm_init(self):
        self.params.mvoc_index_offset = _VOCALGORITHM_VOC_INDEX_OFFSET_DEFAULT
        self.params.mtau_mean_variance_hours = _VOCALGORITHM_TAU_MEAN_VARIANCE_HOURS

        self.params.mgating_max_duration_minutes = (
            _VOCALGORITHM_GATING_MAX_DURATION_MINUTES
        )
        self.params.msraw_std_initial = _VOCALGORITHM_SRAW_STD_INITIAL
        self.params.muptime = 0.0
        self.params.msraw = 0.0
        self.params.mvoc_index = 0.0
        self._vocalgorithm__init_instances()

    def _vocalgorithm__init_instances(self):
        self._vocalgorithm__mean_variance_estimator__init()
        self._vocalgorithm__mean_variance_estimator__set_parameters(
            _VOCALGORITHM_SRAW_STD_INITIAL,
            self.params.mtau_mean_variance_hours,
            self.params.mgating_max_duration_minutes,
        )
        self._vocalgorithm__mox_model__init()
        self._vocalgorithm__mox_model__set_parameters(
            self._vocalgorithm__mean_variance_estimator__get_std(),
            self._vocalgorithm__mean_variance_estimator__get_mean(),
        )
        self._vocalgorithm__sigmoid_scaled__init()
        self._vocalgorithm__sigmoid_scaled__set_parameters(
            self.params.mvoc_index_offset
        )
        self._vocalgorithm__adaptive_lowpass__init()
        self._vocalgorithm__adaptive_lowpass__set_parameters()

    def _vocalgorithm_get_states(self, state0, state1):
        state0 = self._vocalgorithm__mean_variance_estimator__get_mean()
        state1 = self._vocalgorithm__mean_variance_estimator__get_std()
        return state0, state1

    def _vocalgorithm_set_states(self, state0, state1):
        self._vocalgorithm__mean_variance_estimator__set_states(
            state0,
            state1,
            _VOCALGORITHM_PERSISTENCE_UPTIME_GAMMA,
        )
        self.params.msraw = state0

    def _vocalgorithm_set_tuning_parameters(
        self,
        voc_index_offset,
        learning_time_hours,
        gating_max_duration_minutes,
        std_initial,
    ):
        self.params.mvoc_index_offset = float(voc_index_offset)
        self.params.mtau_mean_variance_hours = float(learning_time_hours)
        self.params.mgating_max_duration_minutes = float(gating_max_duration_minutes)
        self.params.msraw_std_initial = float(std_initial)
        self._vocalgorithm__init_instances()

    def process(self, sraw):
        if self.params.muptime <= _VOCALGORITHM_INITIAL_BLACKOUT:
            self.params.muptime += _VOCALGORITHM_SAMPLING_INTERVAL
        else:
            if (sraw > 0) and (sraw < 65000):
                if sraw < 20001:
                    sraw = 20001
                elif sraw > 52767:
                    sraw = 52767
                self.params.msraw = float(sraw - 20000)
            self.params.mvoc_index = self._vocalgorithm__mox_model__process(
                self.params.msraw
            )
            self.params.mvoc_index = self._vocalgorithm__sigmoid_scaled__process(
                self.params.mvoc_index
            )
            self.params.mvoc_index = self._vocalgorithm__adaptive_lowpass__process(
                self.params.mvoc_index
            )
            if self.params.mvoc_index < 0.5:
                self.params.mvoc_index = 0.5
            if self.params.msraw > 0.0:
                self._vocalgorithm__mean_variance_estimator__process(
                    self.params.msraw, self.params.mvoc_index
                )
                self._vocalgorithm__mox_model__set_parameters(
                    self._vocalgorithm__mean_variance_estimator__get_std(),
                    self._vocalgorithm__mean_variance_estimator__get_mean(),
                )
        voc_index = round(self._params.voc_index)
        return voc_index

    def _vocalgorithm__mean_variance_estimator__init(self):
        self._vocalgorithm__mean_variance_estimator__set_parameters(0.0, 0.0, 0.0)
        self._vocalgorithm__mean_variance_estimator___init_instances()

    def _vocalgorithm__mean_variance_estimator___init_instances(self):
        self._vocalgorithm__mean_variance_estimator___sigmoid__init()

    def _vocalgorithm__mean_variance_estimator__set_parameters(
        self, std_initial, tau_mean_variance_hours, gating_max_duration_minutes
    ):
        self.params.m_mean_variance_estimator_gating_max_duration_minutes = (
            gating_max_duration_minutes
        )
        self.params.m_mean_variance_estimator_initialized = False
        self.params.m_mean_variance_estimator_mean = 0.0
        self.params.m_mean_variance_estimator_sraw_offset = 0.0
        self.params.m_mean_variance_estimator_std = std_initial
        self.params.m_mean_variance_estimator_gamma = (
            _VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING
            * (_VOCALGORITHM_SAMPLING_INTERVAL / 3600.0)
        ) / (tau_mean_variance_hours + (_VOCALGORITHM_SAMPLING_INTERVAL / 3600.0))
        self.params.m_mean_variance_estimator_gamma_initial_mean = (
            _VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING
            * _VOCALGORITHM_SAMPLING_INTERVAL
        ) / (_VOCALGORITHM_TAU_INITIAL_MEAN + _VOCALGORITHM_SAMPLING_INTERVAL)
        self.params.m_mean_variance_estimator_gamma_initial_variance = (
            _VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING
            * _VOCALGORITHM_SAMPLING_INTERVAL
        ) / (_VOCALGORITHM_TAU_INITIAL_VARIANCE + _VOCALGORITHM_SAMPLING_INTERVAL)
        self.params.m_mean_variance_estimator_gamma_mean = 0.0
        self.params.m_mean_variance_estimator__gamma_variance = 0.0
        self.params.m_mean_variance_estimator_uptime_gamma = 0.0
        self.params.m_mean_variance_estimator_uptime_gating = 0.0
        self.params.m_mean_variance_estimator_gating_duration_minutes = 0.0

    def _vocalgorithm__mean_variance_estimator__set_states(
        self, mean, std, uptime_gamma
    ):
        self.params.m_mean_variance_estimator_mean = mean
        self.params.m_mean_variance_estimator_std = std
        self.params.m_mean_variance_estimator_uptime_gamma = uptime_gamma
        self.params.m_mean_variance_estimator_initialized = True

    def _vocalgorithm__mean_variance_estimator__get_std(self):
        return self.params.m_mean_variance_estimator_std

    def _vocalgorithm__mean_variance_estimator__get_mean(self):
        return (
            self.params.m_mean_variance_estimator_mean
            + self.params.m_mean_variance_estimator_sraw_offset
        )

    def _vocalgorithm__mean_variance_estimator___calculate_gamma(
        self, voc_index_from_prior
    ):
        uptime_limit = (
            _VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__FIX16_MAX
            - _VOCALGORITHM_SAMPLING_INTERVAL
        )
        if self.params.m_mean_variance_estimator_uptime_gamma < uptime_limit:
            self.params.m_mean_variance_estimator_uptime_gamma = (
                self.params.m_mean_variance_estimator_uptime_gamma
                + _VOCALGORITHM_SAMPLING_INTERVAL
            )

        if self.params.m_mean_variance_estimator_uptime_gating < uptime_limit:
            self.params.m_mean_variance_estimator_uptime_gating = (
                self.params.m_mean_variance_estimator_uptime_gating
                + _VOCALGORITHM_SAMPLING_INTERVAL
            )

        self._vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(
            1.0,
            _VOCALGORITHM_INITI_DURATION_MEAN,
            _VOCALGORITHM_INITI_TRANSITION_MEAN,
        )
        sigmoid_gamma_mean = (
            self._vocalgorithm__mean_variance_estimator___sigmoid__process(
                self.params.m_mean_variance_estimator_uptime_gamma
            )
        )
        gamma_mean = self.params.m_mean_variance_estimator_gamma + (
            (
                self.params.m_mean_variance_estimator_gamma_initial_mean
                - self.params.m_mean_variance_estimator_gamma
            )
            * sigmoid_gamma_mean
        )
        gating_threshold_mean = _VOCALGORITHM_GATING_THRESHOLD + (
            (_VOCALGORITHM_GATING_THRESHOLD_INITIAL - _VOCALGORITHM_GATING_THRESHOLD)
            * self._vocalgorithm__mean_variance_estimator___sigmoid__process(
                self.params.m_mean_variance_estimator_uptime_gating
            )
        )
        self._vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(
            1.0,
            gating_threshold_mean,
            _VOCALGORITHM_GATING_THRESHOLD_TRANSITION,
        )

        sigmoid_gating_mean = (
            self._vocalgorithm__mean_variance_estimator___sigmoid__process(
                voc_index_from_prior
            )
        )
        self.params.m_mean_variance_estimator_gamma_mean = (
            sigmoid_gating_mean * gamma_mean
        )

        self._vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(
            1.0,
            _VOCALGORITHM_INITI_DURATION_VARIANCE,
            _VOCALGORITHM_INITI_TRANSITION_VARIANCE,
        )

        sigmoid_gamma_variance = (
            self._vocalgorithm__mean_variance_estimator___sigmoid__process(
                self.params.m_mean_variance_estimator_uptime_gamma
            )
        )

        gamma_variance = self.params.m_mean_variance_estimator_gamma + (
            (
                self.params.m_mean_variance_estimator_gamma_initial_variance
                - self.params.m_mean_variance_estimator_gamma
            )
            * (sigmoid_gamma_variance - sigmoid_gamma_mean)
        )

        gating_threshold_variance = _VOCALGORITHM_GATING_THRESHOLD + (
            (_VOCALGORITHM_GATING_THRESHOLD_INITIAL - _VOCALGORITHM_GATING_THRESHOLD)
            * self._vocalgorithm__mean_variance_estimator___sigmoid__process(
                self.params.m_mean_variance_estimator_uptime_gating
            )
        )

        self._vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(
            1.0,
            gating_threshold_variance,
            _VOCALGORITHM_GATING_THRESHOLD_TRANSITION,
        )

        sigmoid_gating_variance = (
            self._vocalgorithm__mean_variance_estimator___sigmoid__process(
                voc_index_from_prior
            )
        )

        self.params.m_mean_variance_estimator__gamma_variance = (
            sigmoid_gating_variance * gamma_variance
        )

        self.params.m_mean_variance_estimator_gating_duration_minutes = (
            self.params.m_mean_variance_estimator_gating_duration_minutes
            + (
                (_VOCALGORITHM_SAMPLING_INTERVAL / 60.0)
                * (
                    (
                        (1.0 - sigmoid_gating_mean)
                        * (1.0 + _VOCALGORITHM_GATING_MAX_RATIO)
                    )
                    - _VOCALGORITHM_GATING_MAX_RATIO
                )
            )
        )

        if self.params.m_mean_variance_estimator_gating_duration_minutes < 0.0:
            self.params.m_mean_variance_estimator_gating_duration_minutes = 0.0

        if (
            self.params.m_mean_variance_estimator_gating_duration_minutes
            > self.params.m_mean_variance_estimator_gating_max_duration_minutes
        ):
            self.params.m_mean_variance_estimator_uptime_gating = 0.0

    def _vocalgorithm__mean_variance_estimator__process(
        self, sraw, voc_index_from_prior
    ):
        if not self.params.m_mean_variance_estimator_initialized:
            self.params.m_mean_variance_estimator_initialized = True
            self.params.m_mean_variance_estimator_sraw_offset = sraw
            self.params.m_mean_variance_estimator_mean = 0.0
        else:
            if (self.params.m_mean_variance_estimator_mean >= 100.0) or (
                self.params.m_mean_variance_estimator_mean <= -100.0
            ):
                self.params.m_mean_variance_estimator_sraw_offset = (
                    self.params.m_mean_variance_estimator_sraw_offset
                    + self.params.m_mean_variance_estimator_mean
                )
                self.params.m_mean_variance_estimator_mean = 0.0

            sraw = sraw - self.params.m_mean_variance_estimator_sraw_offset
            self._vocalgorithm__mean_variance_estimator___calculate_gamma(
                voc_index_from_prior
            )
            delta_sgp = (sraw - self.params.m_mean_variance_estimator_mean) / (
                _VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING
            )
            if delta_sgp < 0.0:
                c = self.params.m_mean_variance_estimator_std - delta_sgp
            else:
                c = self.params.m_mean_variance_estimator_std + delta_sgp
            additional_scaling = 1.0
            if c > 1440.0:
                additional_scaling = 4.0
            self.params.m_mean_variance_estimator_std = (
                sqrt(
                    additional_scaling
                    * (
                        _VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING
                        - self.params.m_mean_variance_estimator__gamma_variance
                    )
                )
            ) * sqrt(
                (
                    self.params.m_mean_variance_estimator_std
                    * (
                        self.params.m_mean_variance_estimator_std
                        / (
                            _VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING
                            * additional_scaling
                        )
                    )
                )
                + (
                    (
                        (
                            self.params.m_mean_variance_estimator__gamma_variance
                            * delta_sgp
                        )
                        / additional_scaling
                    )
                    * delta_sgp
                )
            )
            self.params.m_mean_variance_estimator_mean = (
                self.params.m_mean_variance_estimator_mean
                + (self.params.m_mean_variance_estimator_gamma_mean * delta_sgp)
            )

    def _vocalgorithm__mean_variance_estimator___sigmoid__init(self):
        self._vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(
            0.0, 0.0, 0.0
        )

    def _vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(
        self, L, X0, K
    ):
        self.params.m_mean_variance_estimator_sigmoid_l = L
        self.params.m_mean_variance_estimator_sigmoid_k = K
        self.params.m_mean_variance_estimator_sigmoid_x0 = X0

    def _vocalgorithm__mean_variance_estimator___sigmoid__process(self, sample):
        x = self.params.m_mean_variance_estimator_sigmoid_k * (
            sample - self.params.m_mean_variance_estimator_sigmoid_x0
        )
        if x < -50.0:
            return self.params.m_mean_variance_estimator_sigmoid_l
        elif x > 50.0:
            return 0.0
        else:
            return self.params.m_mean_variance_estimator_sigmoid_l / (1.0 + exp(x))

    def _vocalgorithm__mox_model__init(self):
        self._vocalgorithm__mox_model__set_parameters(1.0, 0.0)

    def _vocalgorithm__mox_model__set_parameters(self, SRAW_STD, SRAW_MEAN):
        self.params.m_mox_model_sraw_std = SRAW_STD
        self.params.m_mox_model_sraw_mean = SRAW_MEAN

    def _vocalgorithm__mox_model__process(self, sraw):
        return (
            (sraw - self.params.m_mox_model_sraw_mean)
            / -(self.params.m_mox_model_sraw_std + _VOCALGORITHM_SRAW_STD_BONUS)
        ) * _VOCALGORITHM_VOC_INDEX_GAIN

    def _vocalgorithm__sigmoid_scaled__init(self):
        self._vocalgorithm__sigmoid_scaled__set_parameters(0.0)

    def _vocalgorithm__sigmoid_scaled__set_parameters(self, offset):
        self.params.m_sigmoid_scaled_offset = offset

    def _vocalgorithm__sigmoid_scaled__process(self, sample):
        x = _VOCALGORITHM_SIGMOID_K * (sample - _VOCALGORITHM_SIGMOID_X0)
        if x < -50.0:
            return _VOCALGORITHM_SIGMOID_L
        elif x > 50.0:
            return 0.0
        else:
            if sample >= 0.0:
                shift = (
                    _VOCALGORITHM_SIGMOID_L
                    - (5.0 * self.params.m_sigmoid_scaled_offset)
                ) / 4.0
                return ((_VOCALGORITHM_SIGMOID_L + shift) / (1.0 + exp(x))) - shift
            else:
                return (
                    self.params.m_sigmoid_scaled_offset
                    / _VOCALGORITHM_VOC_INDEX_OFFSET_DEFAULT
                ) * (_VOCALGORITHM_SIGMOID_L / (1.0 + exp(x)))

    def _vocalgorithm__adaptive_lowpass__init(self):
        self._vocalgorithm__adaptive_lowpass__set_parameters()

    def _vocalgorithm__adaptive_lowpass__set_parameters(self):
        self.params.m_adaptive_lowpass_a1 = _VOCALGORITHM_SAMPLING_INTERVAL / (
            _VOCALGORITHM_LP_TAU_FAST + _VOCALGORITHM_SAMPLING_INTERVAL
        )
        self.params.m_adaptive_lowpass_a2 = _VOCALGORITHM_SAMPLING_INTERVAL / (
            _VOCALGORITHM_LP_TAU_SLOW + _VOCALGORITHM_SAMPLING_INTERVAL
        )
        self.params.m_adaptive_lowpass_initialized = False

    def _vocalgorithm__adaptive_lowpass__process(self, sample):
        if not self.params.m_adaptive_lowpass_initialized:
            self.params.m_adaptive_lowpass_x1 = sample
            self.params.m_adaptive_lowpass_x2 = sample
            self.params.m_adaptive_lowpass_x3 = sample
            self.params.m_adaptive_lowpass_initialized = True
        self.params.m_adaptive_lowpass_x1 = (
            (1.0 - self.params.m_adaptive_lowpass_a1)
            * self.params.m_adaptive_lowpass_x1
        ) + (self.params.m_adaptive_lowpass_a1 * sample)

        self.params.m_adaptive_lowpass_x2 = (
            (1.0 - self.params.m_adaptive_lowpass_a2)
            * self.params.m_adaptive_lowpass_x2
        ) + (self.params.m_adaptive_lowpass_a2 * sample)

        abs_delta = (
            self.params.m_adaptive_lowpass_x1 - self.params.m_adaptive_lowpass_x2
        )

        if abs_delta < 0.0:
            abs_delta = -abs_delta
        F1 = exp(_VOCALGORITHM_LP_ALPHA * abs_delta)
        tau_a = ((_VOCALGORITHM_LP_TAU_SLOW - _VOCALGORITHM_LP_TAU_FAST) * F1) + (
            _VOCALGORITHM_LP_TAU_FAST
        )
        a3 = _VOCALGORITHM_SAMPLING_INTERVAL / (_VOCALGORITHM_SAMPLING_INTERVAL + tau_a)
        self.params.m_adaptive_lowpass_x3 = (
            (1.0 - a3) * self.params.m_adaptive_lowpass_x3
        ) + (a3 * sample)
        return self.params.m_adaptive_lowpass_x3
