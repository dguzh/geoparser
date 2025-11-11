# Annotator

The Irchel Geoparser Annotator is a web-based tool for manually annotating toponyms and their corresponding geographic locations in text documents. These annotations can be used for training custom geoparsing models or evaluating geoparser performance.

**This annotator is currently an intermediate solution to restore annotation functionality while the main Irchel Geoparser library undergoes architectural changes.**

The original annotator was built for the legacy version of the Geoparser with a fixed pipeline architecture. Following the geoparser's complete redesign to a modular architecture, we decided against attempting full integration with the new system, as this would require extensive development, and we have instead adapted the annotator to work as a standalone tool for now.
