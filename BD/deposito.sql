CREATE DATABASE  IF NOT EXISTS `deposito` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `deposito`;
-- MySQL dump 10.13  Distrib 8.0.42, for Win64 (x86_64)
--
-- Host: localhost    Database: deposito
-- ------------------------------------------------------
-- Server version	8.0.42

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `categoria`
--

DROP TABLE IF EXISTS `categoria`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `categoria` (
  `id_categoria` int NOT NULL AUTO_INCREMENT,
  `descripcion` varchar(45) NOT NULL,
  PRIMARY KEY (`id_categoria`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `categoria`
--

LOCK TABLES `categoria` WRITE;
/*!40000 ALTER TABLE `categoria` DISABLE KEYS */;
INSERT INTO `categoria` VALUES (1,'Productos'),(2,'Cigarrillos');
/*!40000 ALTER TABLE `categoria` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `factura`
--

DROP TABLE IF EXISTS `factura`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `factura` (
  `id_factura` int NOT NULL AUTO_INCREMENT,
  `fecha` date DEFAULT NULL,
  `nro_telefono` varchar(45) DEFAULT NULL,
  `razon_social` varchar(45) DEFAULT NULL,
  `cliente` varchar(45) DEFAULT NULL,
  `url` varchar(255) DEFAULT NULL,
  `logo` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id_factura`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `factura`
--

LOCK TABLES `factura` WRITE;
/*!40000 ALTER TABLE `factura` DISABLE KEYS */;
/*!40000 ALTER TABLE `factura` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `item_factura`
--

DROP TABLE IF EXISTS `item_factura`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `item_factura` (
  `id_item_factura` int NOT NULL AUTO_INCREMENT,
  `id_factura` int NOT NULL,
  `id_producto` int DEFAULT NULL,
  `cantidad` int DEFAULT NULL,
  `precio_unitario` decimal(12,2) DEFAULT NULL,
  PRIMARY KEY (`id_item_factura`,`id_factura`),
  KEY `id_producto_idx` (`id_producto`),
  KEY `id_factura_idx` (`id_factura`),
  CONSTRAINT `id_factura` FOREIGN KEY (`id_factura`) REFERENCES `factura` (`id_factura`),
  CONSTRAINT `id_producto` FOREIGN KEY (`id_producto`) REFERENCES `producto` (`id_producto`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `item_factura`
--

LOCK TABLES `item_factura` WRITE;
/*!40000 ALTER TABLE `item_factura` DISABLE KEYS */;
/*!40000 ALTER TABLE `item_factura` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `producto`
--

DROP TABLE IF EXISTS `producto`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `producto` (
  `id_producto` int NOT NULL AUTO_INCREMENT,
  `codigo_barra` varchar(45) DEFAULT NULL,
  `descripcion` varchar(45) DEFAULT NULL,
  `costo` decimal(12,2) DEFAULT NULL,
  `ganancia` decimal(5,2) DEFAULT NULL,
  `stock` int DEFAULT '1',
  `tipo_lista` varchar(3) DEFAULT NULL,
  `imprimir` tinyint DEFAULT NULL,
  `codigo_proveedor` varchar(45) DEFAULT NULL,
  `fecha_ult_modificacion` date DEFAULT (curdate()),
  `imagen` varchar(255) DEFAULT NULL,
  `id_categoria` int DEFAULT NULL,
  PRIMARY KEY (`id_producto`),
  KEY `id_categoria_idx` (`id_categoria`),
  KEY `codigo_barra_idx` (`codigo_barra`) /*!80000 INVISIBLE */,
  KEY `descripcion_idx` (`descripcion`),
  CONSTRAINT `id_categoria` FOREIGN KEY (`id_categoria`) REFERENCES `categoria` (`id_categoria`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `producto`
--

LOCK TABLES `producto` WRITE;
/*!40000 ALTER TABLE `producto` DISABLE KEYS */;
INSERT INTO `producto` VALUES (1,NULL,'Alfajo Bon o Bon triple',1057.54,18.00,1,'M',1,'21','2026-07-09',NULL,2),(2,NULL,'Alfajor Aguila mini torta brownie',1057.54,18.00,1,'M',1,'12','2026-07-09',NULL,2),(4,NULL,'Alfajor GOAT',1287.14,20.00,1,'M',1,'23012','2026-07-09',NULL,2),(5,NULL,'Alfajor Guaymallen triple blanco',255.48,18.00,1,'M',1,'59','2026-07-09',NULL,NULL),(6,NULL,'Alfajor Guaymallen triple negro',255.48,18.00,1,'M',1,'58','2026-07-09',NULL,NULL),(7,NULL,'Alfajor Cofler Block triple',1057.54,18.00,1,'M',1,'16','2026-07-09',NULL,2),(8,NULL,'Galletitas diversion',1946.99,18.00,1,'M',1,'1562','2026-07-09',NULL,2);
/*!40000 ALTER TABLE `producto` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `subcategoria`
--

DROP TABLE IF EXISTS `subcategoria`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `subcategoria` (
  `id_subcategoria` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(45) NOT NULL,
  `imprimir` tinyint DEFAULT '1',
  `id_categoria` int DEFAULT NULL,
  PRIMARY KEY (`id_subcategoria`),
  UNIQUE KEY `nombre_UNIQUE` (`nombre`),
  KEY `fk_categoria_idx` (`id_categoria`),
  CONSTRAINT `fk_categoria` FOREIGN KEY (`id_categoria`) REFERENCES `categoria` (`id_categoria`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=45 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `subcategoria`
--

LOCK TABLES `subcategoria` WRITE;
/*!40000 ALTER TABLE `subcategoria` DISABLE KEYS */;
INSERT INTO `subcategoria` VALUES (1,'PILAS',1,1),(2,'SNACKS',1,1),(3,'QUENTO',1,1),(4,'SECHI SRL',1,1),(5,'ARTICULOS VARIOS',1,1),(6,'REPELENTES-INSECTICIDAS',1,1),(7,'TRIO',1,1),(8,'GALLETITAS VARIAS',1,1),(9,'RIERA',1,1),(10,'ARROZ',1,1),(11,'NEVARES',1,1),(12,'DAMA',1,1),(13,'ARCOR',1,1),(14,'SEMILLITAS',1,1),(15,'GRABICH',1,1),(16,'CHOCOLATES',1,1),(17,'LHERITIER',1,1),(18,'FANTOCHE',1,1),(19,'MANTECOL',1,1),(20,'MISKY',1,1),(21,'ALFAJORES',1,1),(22,'KINDER',1,1),(23,'BILLIKEN, STANI-ADAMS',1,1),(24,'GOLOSINAS VARIAS',1,1),(25,'ROYAL',1,1),(26,'PASTAS SECAS',1,1),(27,'VINOS-CERVEZAS-GASEOSAS-FERNET',1,1),(28,'JUGOS',1,1),(29,'GALLETITAS Y SNACKS',1,1),(30,'ACEITS',1,1),(31,'MEDICAMENTOS',1,1),(32,'YERBAS',1,1),(33,'ALIMNTOS Y BEBIDAS',1,1),(34,'ENLATADOS',1,1),(35,'GALLETITAS PASEO',1,1),(36,'ALICANTE',1,1),(37,'PRODUCTOS FRACCIONADOS ARTESANALES',1,1),(38,'MASSALIN',1,2),(39,'TODO TABACO',1,2),(40,'BAT',1,2),(41,'SARANDÍ',1,2),(42,'ESPERT',1,2),(43,'TABACALERA DE SANTIAGO',1,2),(44,'TABACOS VARIOS',1,2);
/*!40000 ALTER TABLE `subcategoria` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-07-23 17:57:46
