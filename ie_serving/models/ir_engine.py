from ie_serving.config import CPU_EXTENSION, DEVICE, PLUGIN_DIR
from openvino.inference_engine import IENetwork, IEPlugin
import glob
import json
from os.path import dirname


class IrEngine():

    def __init__(self, model_xml, model_bin, exec_net, inputs: dict,
                 outputs: list):
        self.model_xml = model_xml
        self.model_bin = model_bin
        self.exec_net = exec_net
        self.input_tensor_names = list(inputs.keys())
        self.input_tensors = inputs
        self.output_tensor_names = outputs
        self.model_keys = self.set_keys()
        self.input_key_names = list(self.model_keys['inputs'].keys())

    @classmethod
    def build(cls, model_xml, model_bin):
        plugin = IEPlugin(device=DEVICE, plugin_dirs=PLUGIN_DIR)
        if CPU_EXTENSION and 'CPU' in DEVICE:
            plugin.add_cpu_extension(CPU_EXTENSION)
        net = IENetwork.from_ir(model=model_xml, weights=model_bin)
        inputs = net.inputs
        batch_size = list(inputs.values())[0][0]
        outputs = net.outputs
        exec_net = plugin.load(network=net, num_requests=batch_size)
        ir_engine = cls(model_xml=model_xml, model_bin=model_bin,
                        exec_net=exec_net, inputs=inputs, outputs=outputs)
        return ir_engine

    def _get_mapping_config_file_if_exists(self):
        parent_dir = dirname(self.model_bin)
        config_path = glob.glob("{}/mapping_config.json".format(parent_dir))
        if len(config_path) == 1:
            try:
                with open(config_path[0], 'r') as f:
                    data = json.load(f)
                return data
            except EnvironmentError:
                print("we cannot open config file")
            except ValueError:
                print("we cannot parse json file")
        return None

    def _return_proper_key_value(self, data: dict, which_way: str,
                                 tensors: list):
        temp_keys = {}
        for input_tensor in tensors:
            if which_way in data:
                if input_tensor in data[which_way]:
                    temp_keys.update({data[which_way][input_tensor]:
                                     input_tensor})
                else:
                    temp_keys.update({input_tensor: input_tensor})
            else:
                temp_keys.update({input_tensor: input_tensor})
        return temp_keys

    def _set_tensor_names_as_keys(self):
        keys_names = {'inputs': {}, 'outputs': {}}
        for input_tensor in self.input_tensor_names:
            keys_names['inputs'].update({input_tensor: input_tensor})
        for output_tensor in self.output_tensor_names:
            keys_names['outputs'].update({output_tensor: output_tensor})
        return keys_names

    def _set_names_in_config_as_keys(self, data: dict):
        keys_names = {'inputs': self.
                      _return_proper_key_value(data=data, which_way='inputs',
                                               tensors=self.
                                               input_tensor_names),
                      'outputs': self.
                      _return_proper_key_value(data=data, which_way='outputs',
                                               tensors=self.
                                               output_tensor_names)}
        return keys_names

    def set_keys(self):
        config_file = self._get_mapping_config_file_if_exists()
        if config_file is None:
            return self._set_tensor_names_as_keys()
        else:
            return self._set_names_in_config_as_keys(config_file)

    def infer(self, data: dict):
        results = self.exec_net.infer(inputs=data)
        return results
