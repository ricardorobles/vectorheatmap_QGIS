from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingException,
                       QgsProcessingOutputNumber,
                       QgsProcessingParameterDistance,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterRasterDestination)
from qgis import processing


class ExampleProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer,
    creates some new layers and returns some results.
    """

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        # Must return a new copy of your algorithm.
        return ExampleProcessingAlgorithm()

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'bufferrasterextend'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('Centralidad')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to.
        """
        return self.tr('Example scripts')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs
        to.
        """
        return 'examplescripts'

    def shortHelpString(self):
        """
        Returns a localised short help string for the algorithm.
        """
        return self.tr('Este algoritmo analiza la centralidad de amenities urbanos')

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """
        # 'INPUT' is the recommended name for the main input
        # parameter.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT',
                self.tr('Input vector layer'),
                types=[QgsProcessing.TypeVectorPoint]
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                'OUTPUT',
                self.tr('Centralidad output'),
            )
        )
        
        
        # 'OUTPUT' is the recommended name for the main output
        # parameter.

        self.addParameter(
            QgsProcessingParameterDistance(
                'BUFFERDIST',
                self.tr('Proximidad'),
                defaultValue = 600.0,
                # Make distance units match the INPUT layer units:
                parentParameterName='INPUT'
            )
        )
        
        self.addParameter(
            QgsProcessingParameterDistance(
                'PIXELSIZE',
                self.tr('Tamaño del pixel'),
                defaultValue = 5.0,
                # Make distance units match the INPUT layer units
                parentParameterName='INPUT'
            )
        )
        
        
        self.addParameter(
            QgsProcessingParameterDistance(
                'CENTRALIDAD',
                self.tr('Centralidad'),
                defaultValue = 0.8,

            )
        )        


    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        # First, we get the count of features from the INPUT layer.
        # This layer is defined as a QgsProcessingParameterFeatureSource
        # parameter, so it is retrieved by calling
        # self.parameterAsSource.
        input_featuresource = self.parameterAsSource(parameters,
                                                     'INPUT',
                                                     context)

        # Retrieve the buffer distance and raster cell size numeric
        # values. Since these are numeric values, they are retrieved
        # using self.parameterAsDouble.
        bufferdist = self.parameterAsDouble(parameters, 'BUFFERDIST',
                                            context)
        
        pixelsize = self.parameterAsDouble(parameters, 'PIXELSIZE',
                                                context)
                                                
                                                
        centralidad = self.parameterAsDouble(parameters, 'CENTRALIDAD',
                                                context)
                                                
        
        if feedback.isCanceled():
            return {}
        heatmap = processing.run("qgis:heatmapkerneldensityestimation", {
                            'INPUT':parameters['INPUT'],
                            'RADIUS':bufferdist,
                            'RADIUS_FIELD':'',
                            'PIXEL_SIZE':pixelsize,
                            'WEIGHT_FIELD':'',
                            'KERNEL':0,
                            'DECAY':0,
                            'OUTPUT_VALUE':0,
                            'OUTPUT':QgsProcessing.TEMPORARY_OUTPUT
                            }, 
            # Because the buffer algorithm is being run as a step in
            # another larger algorithm, the is_child_algorithm option
            # should be set to True
            is_child_algorithm=True,
            #
            # It's important to pass on the context and feedback objects to
            # child algorithms, so that they can properly give feedback to
            # users and handle cancelation requests.
            context=context,
            feedback=feedback)

        # Check for cancelation
        if feedback.isCanceled():
            return {}
            

        # Run the separate rasterization algorithm using the buffer result
        # as an input.
        heatmap_vector = processing.run("gdal:polygonize", {
                            'INPUT':heatmap['OUTPUT'],
                            'BAND':1,
                            'FIELD':'DN',
                            'EIGHT_CONNECTEDNESS':False,
                            'EXTRA':'',
                            'OUTPUT':QgsProcessing.TEMPORARY_OUTPUT
                            },
            is_child_algorithm=True,
            context=context,
            feedback=feedback)

        if feedback.isCanceled():
            return {}
            
        # Calculadora de centralidad    
        centrality = processing.run("native:fieldcalculator", {
                            'INPUT':heatmap_vector['OUTPUT'],
                            'FIELD_NAME':'Centralidad',
                            'FIELD_TYPE':0,
                            'FIELD_LENGTH':100,
                            'FIELD_PRECISION':0,
                            'FORMULA':f'if( "DN" >=(maximum( "DN" )*{centralidad}),1,0)',
                            'OUTPUT':QgsProcessing.TEMPORARY_OUTPUT
                            },
            is_child_algorithm=True,
            context=context,
            feedback=feedback)
            
        if feedback.isCanceled():
            return {}
            
            
        # Extract 0 values    
        extract = processing.run("native:extractbyattribute", {
                            'INPUT':centrality['OUTPUT'],
                            'FIELD':'Centralidad',
                            'OPERATOR':1,
                            'VALUE':'0',
                            'OUTPUT':QgsProcessing.TEMPORARY_OUTPUT
                            },
            is_child_algorithm=True,
            context=context,
            feedback=feedback)
            
            
        if feedback.isCanceled():
            return {}
            
        disuelto = processing.run("native:dissolve", {
                            'INPUT':extract['OUTPUT'],
                            'SEPARATE_DISJOINT':False,
                            'OUTPUT':parameters['OUTPUT']
                            },
            is_child_algorithm=True,
            context=context,
            feedback=feedback)
            
        if feedback.isCanceled():
            return {}

        # Return the results
        context.layerToLoadOnCompletionDetails(disuelto['OUTPUT']).name = f'Centralidad de {bufferdist}m y {centralidad}'
        return disuelto


        