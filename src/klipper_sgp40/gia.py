from math import exp, sqrt


class GasIndexAlgorithm:
    _INDEX_OFFSET_DEFAULT = 100.0
    _LP_TAU_FAST = 20.0
    _LP_TAU_SLOW = 500.0
    _MVE_GAMMA_SCALING = 64.0
    _MVE_ADDITIONAL_GAMMA_MEAN_SCALING = 8.0

    def __init__(self, sampling_interval=1.0):
        """
        Args:
            sampling_interval: Tested from 1 to 10 (seconds)
        """
        self.calibrating = True
        self._sampling_interval = sampling_interval
        self._index_offset = self._INDEX_OFFSET_DEFAULT
        self._sraw_minimum = 20000
        self._gating_max_duration_minutes = 60.0 * 3.0
        self._init_duration_mean = 3600.0 * 0.75
        self._init_duration_variance = 3600.0 * 1.45
        self._gating_threshold = 340.0
        self._index_gain = 230.0
        self._tau_mean_hours = 12.0
        self._tau_variance_hours = 12.0
        self._sraw_std_initial = 50.0
        self._mve_initialized = False
        self._mve_mean = 0.0
        self._mve_sraw_offset = 0.0
        self._mve_std = self._sraw_std_initial
        self._mve_gamma_mean = 0.0
        self._mve_gamma_variance = 0.0
        self._mve_gamma_initial_mean = 0.0
        self._mve_gamma_initial_variance = 0.0
        self.__mve_gamma_mean = 0.0
        self.__mve_gamma_variance = 0.0
        self._mve_uptime_gamma = 0.0
        self._mve_uptime_gating = 0.0
        self._mve_gating_duration_minutes = 0.0
        self._mve_sigmoid_k = 0.0
        self._mve_sigmoid_x0 = 0.0
        self._mox_sraw_std = 0.0
        self._mox_sraw_mean = 0.0
        self._sigmoid_scaled_k = 0.0
        self._sigmoid_scaled_x0 = 0.0
        self._sigmoid_scaled_offset_default = 0.0
        self._adaptive_lowpass_a1 = 0.0
        self._adaptive_lowpass_a2 = 0.0
        self._adaptive_lowpass_initialized = False
        self._adaptive_lowpass_x1 = 0.0
        self._adaptive_lowpass_x2 = 0.0
        self._adaptive_lowpass_x3 = 0.0
        self._uptime = 0.0
        self._sraw = 0.0
        self._gas_index = 0
        self.reset()

    def reset(self):
        """Reset the internal states of the gas index algorithm.

        Previously set tuning parameters are preserved.
        Call this when resuming operation after a measurement interruption.
        """
        self._sraw = 0.0
        self._gas_index = 0
        self._init_instances()

    def get_states(self):
        """Get current algorithm states.

        Retrieved values can be used in set_states() to resume operation
        after a short interruption, skipping initial learning phase.
        """
        return (
            self._mve_offset_mean,
            self._mve_std,
        )

    def set_states(self, mean, std):
        """Set previously retrieved algorithm states to resume operation
        after a short interruption, skipping initial learning phase.

        This feature should not be used after interruptions of more than
        10 minutes. Call this once after construction or reset() and the
        optional set_tuning_parameters(), if desired. Otherwise, the
        algorithm will start with initial learning phase.
        """
        self._mve_set_states(mean, std, 3.0 * 3600.0)
        self._mox_set_parameters(self._mve_std, self._mve_offset_mean)
        self._sraw = mean

    def set_tuning_parameters(
        self,
        index_offset,
        learning_time_offset_hours,
        learning_time_gain_hours,
        gating_max_duration_minutes,
        std_initial,
        gain_factor,
    ):
        self._index_offset = float(index_offset)
        self._tau_mean_hours = float(learning_time_offset_hours)
        self._tau_variance_hours = float(learning_time_gain_hours)
        self._gating_max_duration_minutes = float(gating_max_duration_minutes)
        self._sraw_std_initial = float(std_initial)
        self._index_gain = float(gain_factor)
        self._init_instances()

    @property
    def tuning_parameters(self):
        return {
            "index_offset": int(self._index_offset),
            "learning_time_offset_hours": int(self._tau_mean_hours),
            "learning_time_gain_hours": int(self._tau_variance_hours),
            "gating_max_duration_minutes": int(self._gating_max_duration_minutes),
            "std_initial": int(self._sraw_std_initial),
            "gain_factor": int(self._index_gain),
        }

    @property
    def sampling_interval(self):
        return self._sampling_interval

    def process(self, sraw):
        """Calculate the gas index value from the raw sensor value.

        Args:
            sraw: Raw value from the SGP4x sensor

        Returns:
            Calculated gas index value from the raw sensor value.
            Zero during initial blackout period and 1..500 afterwards
        """
        initial_blackout = 5.0
        if self._uptime <= initial_blackout:
            self._uptime = self._uptime + self._sampling_interval
        else:
            if (sraw > 0) and (sraw < 65000):
                if sraw < (self._sraw_minimum + 1):
                    sraw = self._sraw_minimum + 1
                elif sraw > (self._sraw_minimum + 32767):
                    sraw = self._sraw_minimum + 32767
                self._sraw = float(sraw - self._sraw_minimum)
            self._gas_index = self._mox_process(self._sraw)
            self._gas_index = self._sigmoid_scaled_process(self._gas_index)
            self._gas_index = self._adaptive_lowpass_process(self._gas_index)
            if self._gas_index < 0.5:
                self._gas_index = 0.5
            if self._sraw > 0.0:
                self._mve_process(self._sraw)
                self._mox_set_parameters(self._mve_std, self._mve_offset_mean)
        return round(self._gas_index)

    def _init_instances(self):
        self._mve_set_parameters()
        self._mox_set_parameters(self._mve_std, self._mve_offset_mean)
        self._sigmoid_scaled_set_parameters(213.0, -0.0065, self._INDEX_OFFSET_DEFAULT)
        self._adaptive_lowpass_set_parameters()

    def _mve_set_parameters(self):
        self._mve_initialized = False
        self._mve_mean = 0.0
        self._mve_sraw_offset = 0.0
        self._mve_std = self._sraw_std_initial
        self._mve_gamma_mean = (
            (self._MVE_ADDITIONAL_GAMMA_MEAN_SCALING * self._MVE_GAMMA_SCALING)
            * (self._sampling_interval / 3600.0)
        ) / (self._tau_mean_hours + (self._sampling_interval / 3600.0))
        self._mve_gamma_variance = (
            self._MVE_GAMMA_SCALING * (self._sampling_interval / 3600.0)
        ) / (self._tau_variance_hours + (self._sampling_interval / 3600.0))

        self._mve_gamma_initial_mean = (
            (self._MVE_ADDITIONAL_GAMMA_MEAN_SCALING * self._MVE_GAMMA_SCALING)
            * self._sampling_interval
        ) / (20.0 + self._sampling_interval)

        self._mve_gamma_initial_variance = (
            self._MVE_GAMMA_SCALING * self._sampling_interval
        ) / (2500.0 + self._sampling_interval)
        self.__mve_gamma_mean = 0.0
        self.__mve_gamma_variance = 0.0
        self._mve_uptime_gamma = 0.0
        self._mve_uptime_gating = 0.0
        self._mve_gating_duration_minutes = 0.0

    def _mve_set_states(self, mean, std, uptime_gamma):
        self._mve_sraw_offset = mean
        self._mve_mean = 0.0
        self._mve_std = std
        self._mve_uptime_gamma = uptime_gamma
        self._mve_initialized = True

    @property
    def _mve_offset_mean(self):
        return self._mve_mean + self._mve_sraw_offset

    def _mve_calculate_gamma(self):
        mve_max = 32767.0
        uptime_limit = mve_max - self._sampling_interval
        if self._mve_uptime_gamma < uptime_limit:
            self._mve_uptime_gamma = self._mve_uptime_gamma + self._sampling_interval
        if self._mve_uptime_gating < uptime_limit:
            self._mve_uptime_gating = self._mve_uptime_gating + self._sampling_interval
        self._mve_sigmoid_set_parameters(self._init_duration_mean, 0.01)
        sigmoid_gamma_mean = self._mve_sigmoid_process(self._mve_uptime_gamma)
        gamma_mean = self._mve_gamma_mean + (
            (self._mve_gamma_initial_mean - self._mve_gamma_mean) * sigmoid_gamma_mean
        )
        gating_threshold_initial = 510.0
        gating_threshold_transition = 0.09
        gating_threshold_mean = self._gating_threshold + (
            (gating_threshold_initial - self._gating_threshold)
            * self._mve_sigmoid_process(self._mve_uptime_gating)
        )
        self._mve_sigmoid_set_parameters(
            gating_threshold_mean, gating_threshold_transition
        )
        sigmoid_gating_mean = self._mve_sigmoid_process(self._gas_index)
        self.__mve_gamma_mean = sigmoid_gating_mean * gamma_mean
        self._mve_sigmoid_set_parameters(self._init_duration_variance, 0.01)
        sigmoid_gamma_variance = self._mve_sigmoid_process(self._mve_uptime_gamma)
        gamma_variance = self._mve_gamma_variance + (
            (self._mve_gamma_initial_variance - self._mve_gamma_variance)
            * (sigmoid_gamma_variance - sigmoid_gamma_mean)
        )
        gating_threshold_variance = self._gating_threshold + (
            (gating_threshold_initial - self._gating_threshold)
            * self._mve_sigmoid_process(self._mve_uptime_gating)
        )
        self._mve_sigmoid_set_parameters(
            gating_threshold_variance, gating_threshold_transition
        )
        sigmoid_gating_variance = self._mve_sigmoid_process(self._gas_index)
        self.__mve_gamma_variance = sigmoid_gating_variance * gamma_variance
        max_ratio = 0.3
        self._mve_gating_duration_minutes = self._mve_gating_duration_minutes + (
            (self._sampling_interval / 60.0)
            * (((1.0 - sigmoid_gating_mean) * (1.0 + max_ratio)) - max_ratio)
        )
        if self._mve_gating_duration_minutes < 0.0:
            self._mve_gating_duration_minutes = 0.0
        if self._mve_gating_duration_minutes > self._gating_max_duration_minutes:
            self._mve_uptime_gating = 0.0

    def _mve_process(self, sraw):
        if not self._mve_initialized:
            self._mve_initialized = True
            self._mve_sraw_offset = sraw
            self._mve_mean = 0.0
        else:
            if self._mve_mean >= 100.0 or self._mve_mean <= -100.0:
                self._mve_sraw_offset = self._mve_sraw_offset + self._mve_mean
                self._mve_mean = 0.0
            sraw = sraw - self._mve_sraw_offset
            self._mve_calculate_gamma()
            delta_sgp = (sraw - self._mve_mean) / self._MVE_GAMMA_SCALING
            if delta_sgp < 0.0:
                c = self._mve_std - delta_sgp
            else:
                c = self._mve_std + delta_sgp
            additional_scaling = 1.0
            if c > 1440.0:
                additional_scaling = (c / 1440.0) * (c / 1440.0)
            self._mve_std = sqrt(
                (
                    additional_scaling
                    * (self._MVE_GAMMA_SCALING - self.__mve_gamma_variance)
                )
            ) * sqrt(
                (
                    (
                        self._mve_std
                        * (
                            self._mve_std
                            / (self._MVE_GAMMA_SCALING * additional_scaling)
                        )
                    )
                    + (
                        ((self.__mve_gamma_variance * delta_sgp) / additional_scaling)
                        * delta_sgp
                    )
                )
            )
            self._mve_mean = self._mve_mean + (
                (self.__mve_gamma_mean * delta_sgp)
                / self._MVE_ADDITIONAL_GAMMA_MEAN_SCALING
            )

    def _mve_sigmoid_set_parameters(self, x0, k):
        self._mve_sigmoid_k = k
        self._mve_sigmoid_x0 = x0

    def _mve_sigmoid_process(self, sample):
        if not self.calibrating:
            return 0.0

        x = self._mve_sigmoid_k * (sample - self._mve_sigmoid_x0)
        if x < -50.0:
            return 1.0
        elif x > 50.0:
            return 0.0
        else:
            return 1.0 / (1.0 + exp(x))

    def _mox_set_parameters(self, sraw_std, sraw_mean):
        self._mox_sraw_std = sraw_std
        self._mox_sraw_mean = sraw_mean

    def _mox_process(self, sraw):
        return (
            (sraw - self._mox_sraw_mean) / (-1.0 * (self._mox_sraw_std + 220.0))
        ) * self._index_gain

    def _sigmoid_scaled_set_parameters(self, x0, k, offset_default):
        self._sigmoid_scaled_k = k
        self._sigmoid_scaled_x0 = x0
        self._sigmoid_scaled_offset_default = offset_default

    def _sigmoid_scaled_process(self, sample):
        sigmoid_l = 500.0
        x = self._sigmoid_scaled_k * (sample - self._sigmoid_scaled_x0)
        if x < -50.0:
            return sigmoid_l
        elif x > 50.0:
            return 0.0
        else:
            if sample >= 0.0:
                if self._sigmoid_scaled_offset_default == 1.0:
                    shift = (500.0 / 499.0) * (1.0 - self._index_offset)
                else:
                    shift = (sigmoid_l - (5.0 * self._index_offset)) / 4.0
                return ((sigmoid_l + shift) / (1.0 + exp(x))) - shift
            else:
                return (self._index_offset / self._sigmoid_scaled_offset_default) * (
                    sigmoid_l / (1.0 + exp(x))
                )

    def _adaptive_lowpass_set_parameters(self):
        self._adaptive_lowpass_a1 = self._sampling_interval / (
            self._LP_TAU_FAST + self._sampling_interval
        )
        self._adaptive_lowpass_a2 = self._sampling_interval / (
            self._LP_TAU_SLOW + self._sampling_interval
        )
        self._adaptive_lowpass_initialized = False

    def _adaptive_lowpass_process(self, sample):
        if not self._adaptive_lowpass_initialized:
            self._adaptive_lowpass_x1 = sample
            self._adaptive_lowpass_x2 = sample
            self._adaptive_lowpass_x3 = sample
            self._adaptive_lowpass_initialized = True

        self._adaptive_lowpass_x1 = (
            (1.0 - self._adaptive_lowpass_a1) * self._adaptive_lowpass_x1
        ) + (self._adaptive_lowpass_a1 * sample)
        self._adaptive_lowpass_x2 = (
            (1.0 - self._adaptive_lowpass_a2) * self._adaptive_lowpass_x2
        ) + (self._adaptive_lowpass_a2 * sample)
        abs_delta = self._adaptive_lowpass_x1 - self._adaptive_lowpass_x2
        if abs_delta < 0.0:
            abs_delta = -1.0 * abs_delta

        f1 = exp(-0.2 * abs_delta)
        tau_a = ((self._LP_TAU_SLOW - self._LP_TAU_FAST) * f1) + self._LP_TAU_FAST
        a3 = self._sampling_interval / (self._sampling_interval + tau_a)
        self._adaptive_lowpass_x3 = ((1.0 - a3) * self._adaptive_lowpass_x3) + (
            a3 * sample
        )
        return self._adaptive_lowpass_x3


# Copyright (c) 2022, Sensirion AG
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of Sensirion AG nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
